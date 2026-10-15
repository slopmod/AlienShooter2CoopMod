"""Keep OLD quest numbering while loading optional Reloaded road stages."""
import hashlib


def prepare_definitions(root):
    from old_native_campaign_progression import once
    original = (root / 'Maps/common_defs2.lgc').read_bytes()
    if hashlib.sha256(original).hexdigest() != '09ee502c90e701b8a6b8f5025a25aac9442c8ba2e2c175956e8d5822319e6795':
        raise ValueError('Unsupported OLD campaign definitions')
    source = original.decode('cp1251').replace('\r\n', '\n')
    source = once(source, '    //check, if level number is correct', '''#ifdef COOP_CAMPAIGN
    // Imported road stages share the original level-seven quest database.
    // Checkpoint IDs 72/73 never reach the native fixed-size level arrays.
    if(!bSurvive && (sCurMapName == "maps\\\\level_07_2.map"
        || sCurMapName == "maps\\\\level_07_3.map"))
    {
        NewLevNum = 7;
        bCorrect = true;
    }
#endif
    //check, if level number is correct''')
    source = once(source, 'if(NewLevNum < iMaxLevel && GetLevelName(NewLevNum, bSurvive) == sCurMapName)',
                  'if(bCorrect || (NewLevNum < iMaxLevel && GetLevelName(NewLevNum, bSurvive) == sCurMapName))')
    source += '\n// Imported car registration callback.\nF3100_15(int unit);\n'
    return source
