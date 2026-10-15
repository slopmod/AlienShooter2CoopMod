"""Portable, atomic campaign checkpoints and a local launcher file bridge.

The game performs native serialization on its own thread. This worker only
validates/copies files and publishes completion receipts; it never reads or
writes process memory. The client receives the selected checkpoint over the
existing pre-game DirectPlay channels, not a second network server.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
import zlib

from old_native_campaign_patch import BASELINE_SHA256
from old_native_campaign_missions import MAP_NUMBERS, mission_by_number
from old_native_localization import tr

SCHEMA=1
LIMIT=262144
CHUNK=240
MAX_CHUNKS=2048
NATIVE_KINDS=('0','3','quests')
MAX_MENU_SAVES=4096
MENU_TIMEZONE=timezone(timedelta(hours=5))  # Asia/Qyzylorda at the supported campaign dates.


def menu_date(created):
    value=datetime.fromisoformat(created)
    if value.tzinfo is None:value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(MENU_TIMEZONE).strftime('%d.%m.%Y %H:%M:%S')


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode('ascii')


def atomic(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as file:
            file.write(data);file.flush();os.fsync(file.fileno())
        for attempt in range(8):
            try:
                os.replace(temporary,path)
                break
            except PermissionError:
                # A native FOpen reader can briefly deny replacement on Windows.
                if attempt==7:raise
                time.sleep(.01)
    finally:
        temporary.unlink(missing_ok=True)


def native_lines(text):
    return [line for line in text.replace('\r\n','\n').splitlines() if line and not line.startswith(';')]


def hero_fields(text):
    fields={}
    lines=native_lines(text)
    if len(text.encode('cp1251'))>65536 or not lines:raise ValueError('Invalid hero size')
    for line in lines:
        if len(line)>16000 or '=' not in line or '\x00' in line:raise ValueError('Invalid native hero row')
        key,value=line.split('=',1)
        if key in fields:raise ValueError('Duplicate hero property')
        if not re.fullmatch(r'[A-Za-z_]+(?::INV_[A-Z_0-9]+)?',key):raise ValueError('Invalid hero property')
        if not re.fullmatch(r'[A-Za-z0-9_.,<>\[\](){}|+ -]+',value):raise ValueError('Invalid hero value')
        fields[key]=value
    if not re.fullmatch(r'Char[1-8]',fields.get('Character','')):raise ValueError('Unsupported character')
    for key in ('Exp','Rank','Money','SkillsToAdd','HeroColor'):
        value=fields.get(key,'')
        if not value.isdigit() or not 0<=int(value)<=2147483647:raise ValueError('Invalid hero '+key)
    if int(fields['HeroColor'])>7:raise ValueError('Invalid hero color')
    if not any(k.startswith('Inv:') for k in fields):raise ValueError('Missing inventory')
    return fields


def validate(data):
    if not isinstance(data,dict) or set(data)!={'schema','native_build','id','created','mission','health','native','sha256'}:
        raise ValueError('Unknown checkpoint structure')
    if data['schema']!=SCHEMA or data['native_build']!=BASELINE_SHA256:raise ValueError('Incompatible checkpoint version')
    if type(data['mission']) is not int or data['mission'] not in MAP_NUMBERS:raise ValueError('Unsupported saved mission')
    if type(data['health']) is not int or data['health'] not in (0,1):raise ValueError('Invalid saved health setting')
    if not isinstance(data['id'],str) or not re.fullmatch('[0-9a-f]{32}',data['id']):raise ValueError('Invalid checkpoint ID')
    datetime.fromisoformat(data['created'])
    if not isinstance(data['native'],dict) or set(data['native'])!=set(NATIVE_KINDS):raise ValueError('Incomplete checkpoint')
    for value in data['native'].values():
        if not isinstance(value,str) or len(value)>65536 or '\x00' in value:raise ValueError('Invalid native payload')
        value.encode('cp1251')
    for army in ('0','3'):hero_fields(data['native'][army])
    # Native quest records are numeric IDs/states. Comments carry filenames.
    for line in native_lines(data['native']['quests']):
        if len(line)>512 or not re.fullmatch(r'[A-Za-z0-9_=,;:|. +\-\[\]\t]+',line):
            raise ValueError('Invalid native quest record')
    body={k:v for k,v in data.items() if k!='sha256'}
    if hashlib.sha256(canonical(body)).hexdigest()!=data['sha256']:raise ValueError('Checkpoint checksum mismatch')
    if len(canonical(data))>LIMIT:raise ValueError('Checkpoint too large')
    return data


def create(native,mission,health):
    body=dict(schema=SCHEMA,native_build=BASELINE_SHA256,id=uuid.uuid4().hex,
              created=datetime.now(timezone.utc).isoformat(timespec='seconds'),
              mission=mission,health=health,native=native)
    body['sha256']=hashlib.sha256(canonical(body)).hexdigest()
    return validate(body)


def load(path):
    path=Path(path)
    if path.stat().st_size>LIMIT:raise ValueError('Checkpoint too large')
    return validate(json.loads(path.read_text('utf-8')))


def list_saves(folder):
    values=[]
    for path in Path(folder).glob('*.as2coop.json'):
        try:
            data=load(path)
            date=datetime.fromisoformat(data['created']).astimezone().strftime('%d.%m.%Y %H:%M:%S')
            title=tr('Миссия ', 'Mission ')+mission_by_number(data['mission']).label+' — '+date
            values.append((data['created'],path,title))
        except (OSError,ValueError,TypeError,KeyError):continue
    return sorted(values,reverse=True,key=lambda item:(item[0],item[1].name))


def stage(folder,data):
    validate(data)
    for kind,text in data['native'].items():atomic(folder/f'coop-in-{kind}.txt',text.encode('cp1251'))
    atomic(folder/'coop-resume-state.txt',('READY:'+data['sha256']+'\n').encode())


def wire(data,*,chunk_size=CHUNK):
    if type(chunk_size) is not int or not 2<=chunk_size<=CHUNK or chunk_size%2:
        raise ValueError('Invalid checkpoint chunk size')
    raw=zlib.compress(canonical(validate(data)),9).hex()
    chunks=[raw[i:i+chunk_size] for i in range(0,len(raw),chunk_size)]
    if not 1<=len(chunks)<=MAX_CHUNKS:raise ValueError('Checkpoint transport capacity')
    heroes=[hero_fields(data['native'][army]) for army in ('0','3')]
    header=':'.join(map(str,['S1',data['mission'],heroes[0]['Character'][4:],heroes[0]['HeroColor'],
        heroes[1]['Character'][4:],heroes[1]['HeroColor'],len(chunks),data['sha256'],data['health']]))
    return header,chunks


class CheckpointService:
    def __init__(self,folders,saves,selected=None):
        self.folders=[Path(p) for p in folders];self.saves=Path(saves)
        self.preset=Path(selected) if selected else None
        preset=load(self.preset) if self.preset else None
        self.selected={folder:preset for folder in self.folders}
        # This belongs to the running campaign, not the newest entry on disk.
        # Starting NEW clears it; the creation barrier saves mission 1 before
        # loading the map, and each durable onward checkpoint replaces it.
        self.last_checkpoint={folder:preset for folder in self.folders}
        # Survives map VM reloads so repeated local GetTime/nonces cannot
        # accept a previous retry's in-flight network messages.
        self.retry_attempt={folder:0 for folder in self.folders}
        self.expected={};self.seen={};self.errors=[]
        self.menu_nonce={folder:0 for folder in self.folders}
        self.catalog={};self.unavailable=0
        self._scan_catalog()
        for folder in self.folders:
            # These are fixed bridge staging files only; durable saves live elsewhere.
            for name in ('coop-save.pending.txt','coop-save-status.txt','coop-incoming.txt',
                         'coop-resume-proof.txt','coop-resume-state.txt','coop-resume-mode.txt','coop-resume-wire.txt',
                         'coop-resume-request.txt','coop-menu-request.txt','coop-menu-status.txt',
                         'coop-menu-catalog.txt','coop-retry-request.txt','coop-retry-status.txt',
                         'coop-retry-attempt.txt'):
                (folder/name).unlink(missing_ok=True)
            atomic(folder/'coop-resume-mode.txt',b'NEW\n')
            atomic(folder/'coop-resume-state.txt',b'WAIT\n')
            atomic(folder/'coop-save-status.txt',b'WAIT\n')
            atomic(folder/'coop-retry-status.txt',b'WAIT\n')
            self._select(folder,preset)
            self._publish_menu(folder)

    def _scan_catalog(self):
        """Only catalog UUIDs are selectable; requests never supply a filesystem path.

        Distinct content with a duplicated UUID is ambiguous and unavailable. Exact
        copies count once. A preset outside the usual save directory stays selectable.
        """
        paths=list(self.saves.glob('*.as2coop.json'))
        if self.preset and self.preset not in paths:paths.append(self.preset)
        entries={};counts={};conflicts=set();unavailable=0
        for path in paths:
            try:
                data=load(path);wire(data)
            except (OSError,ValueError,TypeError,KeyError):
                unavailable+=1;continue
            key=data['id'];counts[key]=counts.get(key,0)+1
            if key in entries and entries[key][1]['sha256']!=data['sha256']:
                conflicts.add(key)
            else:entries[key]=(path,data)
        for key in conflicts:
            entries.pop(key,None);unavailable+=counts[key]
        ordered=sorted(entries.items(),key=lambda pair:(pair[1][1]['created'],pair[0]),reverse=True)
        self.unavailable=unavailable+max(0,len(ordered)-MAX_MENU_SAVES)
        self.catalog=dict(ordered[:MAX_MENU_SAVES])

    def _publish_menu(self,folder,status='OK',error='NONE',*,receipt=True):
        """ASCII line protocol; catalog rows always have exactly six fields.

        Catalog: AS2CATALOG1, nonce, selected UUID/NEW, count, unavailable count,
        then (UUID, mission, date, host label, guest label, health) per row, END.
        Receipt: nonce, OK/ERROR, selected UUID/NEW, error code. Publish it last.
        """
        selected=self.selected[folder]
        key=selected['id'] if selected else 'NEW'
        nonce=str(self.menu_nonce[folder])
        lines=['AS2CATALOG1',nonce,key,str(len(self.catalog)),str(self.unavailable)]
        for _,data in self.catalog.values():
            heroes=[hero_fields(data['native'][army]) for army in ('0','3')]
            labels=[f"{hero['Character']} / XP {int(hero['Exp'])}" for hero in heroes]
            lines.extend([data['id'],str(data['mission']),menu_date(data['created']),*labels,str(data['health'])])
        lines.append('END')
        atomic(folder/'coop-menu-catalog.txt',('\n'.join(lines)+'\n').encode('ascii'))
        if receipt:
            atomic(folder/'coop-menu-status.txt',('\n'.join([nonce,status,key,error])+'\n').encode('ascii'))

    def _select(self,folder,data,*,remember=True,chunk_size=CHUNK):
        # The UI waits for this transaction's nonce receipt before starting a host.
        for name in ('coop-resume-request.txt','coop-resume-proof.txt','coop-incoming.txt'):
            path=folder/name;path.unlink(missing_ok=True);self.seen.pop(path,None)
        self.expected.pop(folder,None)
        if data is None:
            for kind in NATIVE_KINDS:
                (folder/f'coop-in-{kind}.txt').unlink(missing_ok=True)
                (folder/f'coop-proof-{kind}.txt').unlink(missing_ok=True)
            (folder/'coop-resume-wire.txt').unlink(missing_ok=True)
            atomic(folder/'coop-resume-state.txt',b'WAIT\n')
            atomic(folder/'coop-resume-mode.txt',b'NEW\n')
        else:
            header,chunks=wire(data,chunk_size=chunk_size)
            stage(folder,data)
            atomic(folder/'coop-resume-wire.txt',('\n'.join(chunks)+'\n').encode('ascii'))
            atomic(folder/'coop-resume-mode.txt',(header+'\n').encode('ascii'))
            self.expected[folder]=data
        self.selected[folder]=data
        if remember:
            self.last_checkpoint[folder]=data
            retry=folder/'coop-retry-request.txt'
            retry.unlink(missing_ok=True);self.seen.pop(retry,None)
            (folder/'coop-retry-attempt.txt').unlink(missing_ok=True)
            atomic(folder/'coop-retry-status.txt',b'WAIT\n')

    def _menu(self,folder):
        lines=self._read_once(folder/'coop-menu-request.txt')
        if lines is None:return
        if len(lines)!=5 or lines[0]!='AS2MENU1' or not re.fullmatch(r'[1-9][0-9]{0,9}',lines[1]):
            raise ValueError('Invalid menu request')
        nonce=int(lines[1])
        if nonce>2147483647:raise ValueError('Invalid menu nonce')
        if nonce<=self.menu_nonce[folder]:return  # Never replace a newer receipt with a stale one.
        self.menu_nonce[folder]=nonce
        operation,key=lines[2:4]
        try:
            if operation=='REFRESH' and key=='NEW':self._scan_catalog()
            elif operation=='SELECT':
                if key=='NEW':self._select(folder,None)
                else:
                    if not re.fullmatch('[0-9a-f]{32}',key) or key not in self.catalog:
                        raise ValueError('Unknown checkpoint ID')
                    path,listed=self.catalog[key]
                    data=load(path)
                    if data['id']!=key or data['sha256']!=listed['sha256']:
                        raise ValueError('Checkpoint changed since catalog refresh')
                    self._select(folder,data)
            else:raise ValueError('Invalid menu operation')
        except (OSError,ValueError,KeyError,TypeError) as error:
            self.errors.append(str(error))
            self._publish_menu(folder,'ERROR','INVALID_SELECTION' if operation=='SELECT' else 'INVALID_REQUEST')
            return
        self._publish_menu(folder)

    def _read_once(self,path):
        try:
            if path.stat().st_size>LIMIT*2:raise ValueError('Bridge file too large')
            raw=path.read_bytes()
        except FileNotFoundError:return None
        if not raw.endswith(b'END\r\n') and not raw.endswith(b'END\n'):return None
        digest=(path.stat().st_mtime_ns,hashlib.sha256(raw).hexdigest())
        if self.seen.get(path)==digest:return None
        self.seen[path]=digest
        return raw.decode('ascii').splitlines()

    def poll(self):
        for folder in self.folders:
            for operation in (self._menu,self._request,self._receive,self._proof,self._save,self._retry):
                try:operation(folder)
                except (OSError,ValueError,KeyError,TypeError,zlib.error) as error:
                    self.errors.append(str(error))
                    if operation==self._menu:self._publish_menu(folder,'ERROR','INVALID_REQUEST')
                    elif operation==self._retry:
                        atomic(folder/'coop-retry-status.txt',b'0\nERROR\nINVALID_REQUEST\nEND\n')
                    else:
                        name='coop-save-status.txt' if operation==self._save else 'coop-resume-state.txt'
                        atomic(folder/name,b'ERROR\n')
                    print('Checkpoint:',error,flush=True)

    def _request(self,folder):
        lines=self._read_once(folder/'coop-resume-request.txt')
        if lines is None:return
        selected=self.selected[folder]
        if not selected or lines!=[selected['sha256'],'END']:
            raise ValueError('Unexpected host checkpoint selection')
        stage(folder,selected);self.expected[folder]=selected

    def _receive(self,folder):
        lines=self._read_once(folder/'coop-incoming.txt')
        if lines is None:return
        if len(lines)<3 or not re.fullmatch('[0-9a-f]{64}',lines[0]):raise ValueError('Bad checkpoint transfer header')
        chunks=lines[1:-1]
        if len(chunks)>MAX_CHUNKS or any(not re.fullmatch('[0-9a-f]{2,240}',s) or len(s)%2 for s in chunks):
            raise ValueError('Bad checkpoint chunks')
        decoder=zlib.decompressobj();raw=decoder.decompress(bytes.fromhex(''.join(chunks)),LIMIT+1)
        if len(raw)>LIMIT or not decoder.eof or decoder.unused_data:raise ValueError('Bad compressed checkpoint')
        data=validate(json.loads(raw))
        if data['sha256']!=lines[0]:raise ValueError('Transfer checksum mismatch')
        stage(folder,data);self.expected[folder]=data

    def _proof(self,folder):
        lines=self._read_once(folder/'coop-resume-proof.txt')
        if lines is None:return
        data=self.expected.get(folder)
        if not data or lines!=[data['sha256'],'END']:raise ValueError('Unexpected native restore proof')
        for kind in NATIVE_KINDS:
            actual=(folder/f'coop-proof-{kind}.txt').read_text('cp1251')
            if native_lines(actual)!=native_lines(data['native'][kind]):
                raise ValueError('Native restore differs: '+kind)
        atomic(folder/'coop-resume-state.txt',('OK:'+data['sha256']+'\n').encode())
        self.last_checkpoint[folder]=data

    def _retry(self,folder):
        """Restage this campaign's last checkpoint for a connected retry lobby.

        Request: AS2RETRY1, positive nonce, END. The game writes WAIT to the
        status before each request, then waits for this nonce's receipt. Map
        clocks/nonces may restart, so only complete file rewrites are deduped
        by _read_once; nonce ordering is deliberately not compared globally.
        Success: nonce, READY, SHA256, mission, END. Failure: nonce, ERROR,
        NO_CHECKPOINT/RESTORE_FAILED, END. The game must not load on failure.
        Before READY: coop-retry-attempt.txt = nonce, process-monotonic attempt,
        SHA256, END. The connected lobby envelopes messages with that attempt.
        The existing S1 transfer/proof barrier still owns native restoration.
        """
        lines=self._read_once(folder/'coop-retry-request.txt')
        if lines is None:return
        if (len(lines)!=3 or lines[0]!='AS2RETRY1'
                or not re.fullmatch(r'[1-9][0-9]{0,9}',lines[1])
                or int(lines[1])>2147483647):
            raise ValueError('Invalid campaign retry request')
        nonce=lines[1]
        data=self.last_checkpoint[folder]
        if data is None:
            atomic(folder/'coop-retry-status.txt',
                   f'{nonce}\nERROR\nNO_CHECKPOINT\nEND\n'.encode('ascii'))
            return
        try:
            validate(data)
            if self.retry_attempt[folder]>=2147483647:raise ValueError('Campaign retry attempt limit')
            self.retry_attempt[folder]+=1
            # Retry messages carry a session-attempt envelope. Reserve room
            # under DirectPlay's existing short script-message limit.
            self._select(folder,data,remember=False,chunk_size=192)
            atomic(folder/'coop-retry-attempt.txt',
                   f"{nonce}\n{self.retry_attempt[folder]}\n{data['sha256']}\nEND\n".encode('ascii'))
        except (OSError,ValueError,KeyError,TypeError) as error:
            self.errors.append('Campaign retry: '+str(error))
            atomic(folder/'coop-retry-status.txt',
                   f'{nonce}\nERROR\nRESTORE_FAILED\nEND\n'.encode('ascii'))
            return
        atomic(folder/'coop-retry-status.txt',
               f"{nonce}\nREADY\n{data['sha256']}\n{data['mission']}\nEND\n".encode('ascii'))

    def _save(self,folder):
        lines=self._read_once(folder/'coop-save.pending.txt')
        if lines is None:return
        if len(lines)!=4 or lines[0]!='AS2CHECKPOINT1':raise ValueError('Incomplete native checkpoint')
        mission,health=int(lines[1]),int(lines[2])
        native={kind:(folder/f'coop-out-{kind}.txt').read_text('cp1251') for kind in NATIVE_KINDS}
        data=create(native,mission,health)
        path=self.saves/(datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-')+data['id']+'.as2coop.json')
        atomic(path,canonical(data)+b'\n')
        self.last_checkpoint[folder]=data
        atomic(folder/'coop-save-status.txt',b'SAVED\n')
        print(tr('Автосохранение: ', 'Autosave: ')+str(path),flush=True)
        # The lobby can be reopened without restarting the launcher. Publish
        # the new durable checkpoint to every local browser immediately, while
        # preserving each peer's selection and its last request receipt.
        # A presentation failure must not turn an already durable save into an
        # ERROR acknowledgement; reopening/refreshing the browser retries it.
        try:
            self._scan_catalog()
            for peer in self.folders:self._publish_menu(peer,receipt=False)
        except (OSError,ValueError,KeyError,TypeError) as error:
            self.errors.append('Menu catalog refresh: '+str(error))
            print('Checkpoint menu refresh:',error,flush=True)
