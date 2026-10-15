"""Local drag gesture over owned locators; one acknowledged command on drop."""

SCRIPT = r'''
static int OldInventoryDragArmed = 0;
static int OldInventoryDragActive = 0;
static int OldInventoryDragLastDown = 0;
static int OldInventoryDragSprite = 0;
static int OldInventoryDragStartX = 0;
static int OldInventoryDragStartY = 0;
static int OldInventoryDragDrawX = 0;
static int OldInventoryDragDrawY = 0;
static int OldInventoryDragOffsetX = 0;
static int OldInventoryDragOffsetY = 0;
static int OldInventoryDragWidth = 0;
static int OldInventoryDragHeight = 0;
static int OldInventoryDragQuote = 0;
static int OldInventoryDragTarget = -1;
static int OldInventoryDragAllowed = 0;
static int OldInventoryDragRefresh = 0;
static int OldInventoryDragTwice = 0;
static int OldInventoryDragKind = 0;
static int OldInventoryDragPrice = 0;
OldInventoryDragShopArea(int x, int y);

OldInventoryDragCancel()
{
    if(OldInventoryDragSprite) Destroy(OldInventoryDragSprite);
    OldInventoryDragSprite = 0;
    OldInventoryDragArmed = 0;
    OldInventoryDragActive = 0;
    OldInventoryDragTarget = -1;
    OldInventoryDragAllowed = 0;
    OldInventoryDragRefresh = 0;
    OldInventoryDragKind = 0;
}

OldInventoryDragReset(int army)
{
    OldInventoryDragCancel();
    OldInventoryDragLastDown = SendCommandA(army, 329, IM_LBUTTONDOWN);
    OldStockInventoryClickTime = 0;
}

OldInventoryDragStart(int army, int locator, int x, int y)
{
    if(locator < 0 || SendCommandA(army, 326) || SendCommandA(0, 327)) return;
    OldInventoryDragCancel();
    OldInventoryDragKind = 1;
    OldInventoryDragTwice = locator == OldStockInventoryLocator &&
        SendCommandA(army, 312, locator, 0) == OldStockInventoryBase &&
        OldStockInventoryClickTime && GetTime()-OldStockInventoryClickTime < 450;
    OldStockInventorySelect(army, locator);
    OldShopLocalQueueResult = 0;
    if(OldStockInventoryBase < 1 || OldStockInventoryBase > 4096 ||
       OldStockInventoryQuantity < 1 || OldStockInventoryQuantity > 262143) return;
    OldInventoryDragQuote = OldStockInventoryBase+OldStockInventoryQuantity*8192;
    OldInventoryDragWidth = SendCommandA(army, 312, locator, 16);
    OldInventoryDragHeight = SendCommandA(army, 312, locator, 17);
    if(OldInventoryDragWidth < 1 || OldInventoryDragHeight < 1) return;
    OldInventoryDragOffsetX = 0;
    OldInventoryDragOffsetY = 0;
    int cell = SendCommandA(army, 340, x, y);
    if(locator < 4096 && cell >= 0 && cell < 4096)
    {
        OldInventoryDragOffsetX = cell/64-locator/64;
        OldInventoryDragOffsetY = cell%64-locator%64;
    }
    OldInventoryDragStartX = x;
    OldInventoryDragStartY = y;
    OldInventoryDragArmed = 1;
    OldStockItemInfoClear(army);
}

OldInventoryDragCatalogStart(int army, int base, int x, int y, int left, int top)
{
    if(SendCommandA(army, 326) || SendCommandA(0, 327)) return;
    OldInventoryDragCancel();
    OldStockInventoryBase = base;
    OldStockInventoryQuantity = SendCommandA(0, 303, base, 2);
    OldStockInventoryLocator = -1;
    if(base < 1 || base > 4096 || OldStockInventoryQuantity < 1 || OldStockInventoryQuantity > 262143) return;
    OldInventoryDragWidth = SendCommandA(0, 303, base, 16);
    OldInventoryDragHeight = SendCommandA(0, 303, base, 17);
    if(OldInventoryDragWidth < 1 || OldInventoryDragHeight < 1) return;
    OldInventoryDragPrice = SendCommandA(0, 303, base, 1);
    OldInventoryDragQuote = base+OldStockInventoryQuantity*8192;
    OldInventoryDragOffsetX = (x-left)/37;
    OldInventoryDragOffsetY = (y-top)/37;
    OldInventoryDragStartX = x;
    OldInventoryDragStartY = y;
    OldInventoryDragKind = 2;
    OldInventoryDragTwice = 0;
    OldInventoryDragArmed = 1;
    OldStockInventoryClickTime = 0;
    OldShopLocalQueueResult = 0;
    OldStockItemInfoClear(army);
}

OldInventoryDragTargetAt(int army, int x, int y)
{
    if(OldInventoryDragKind == 1 && OldInventoryDragShopArea(x, y)) return 2097152;
    int cell = SendCommandA(army, 340, x, y);
    if(cell < 0) return -1;
    if(cell >= 65536) return cell/65536*65536;
    int cx = cell/64-OldInventoryDragOffsetX;
    int cy = cell%64-OldInventoryDragOffsetY;
    if(cx < 0 || cy < 0) return -1;
    return cx*64+cy;
}

OldInventoryDragTact(int army, int down, int hovered, int x, int y)
{
    int pressed = down && !OldInventoryDragLastDown;
    int released = !down && OldInventoryDragLastDown;
    OldInventoryDragLastDown = down;
    if(pressed) OldInventoryDragStart(army, hovered, x, y);
    if(!OldInventoryDragArmed) return;
    int stale = SendCommandA(army, 326) || SendCommandA(0, 327);
    if(OldInventoryDragKind == 1)
        stale = stale || SendCommandA(army, 312, OldStockInventoryLocator, 0) != OldStockInventoryBase ||
            SendCommandA(army, 312, OldStockInventoryLocator, 3) != OldStockInventoryQuantity;
    else
        stale = stale || SendCommandA(0, 303, OldStockInventoryBase, 2) != OldStockInventoryQuantity ||
            SendCommandA(0, 303, OldStockInventoryBase, 1) != OldInventoryDragPrice;
    if(stale)
    {
        OldInventoryDragCancel();
        OldStockInventoryClickTime = 0;
        OldShopLocalQueueResult = -7;
        return;
    }
    if(!OldInventoryDragActive &&
       (Abs(x-OldInventoryDragStartX) >= 5 || Abs(y-OldInventoryDragStartY) >= 5))
    {
        OldInventoryDragActive = 1;
        OldStockInventoryClickTime = 0;
        int vid = SendCommandA(army, EXT_GETITEMVIDBYID, OldStockInventoryBase, 1);
        int dir = SendCommandA(army, EXT_GETITEMVIDBYID, OldStockInventoryBase, 2);
        OldInventoryDragDrawX = x+(OldInventoryDragWidth*37)/2-OldInventoryDragOffsetX*37-18;
        OldInventoryDragDrawY = y+(OldInventoryDragHeight*37)/2-OldInventoryDragOffsetY*37-18;
        if(vid > 0 && dir >= 0)
            OldInventoryDragSprite = OldUiVisual(vid, SendCommand(EXT_GETABSDIR, vid, dir),
                OldInventoryDragDrawX, OldInventoryDragDrawY, 1000, 1000, 4100);
    }
    if(OldInventoryDragActive)
    {
        OldStockItemInfoClear(army);
        int dx = x+(OldInventoryDragWidth*37)/2-OldInventoryDragOffsetX*37-18;
        int dy = y+(OldInventoryDragHeight*37)/2-OldInventoryDragOffsetY*37-18;
        int spr = OldInventoryDragSprite;
        if(spr) Action(spr, ACT_CHANGE_COOR, GetX(spr)+dx-OldInventoryDragDrawX,
            GetY(spr)+dy-OldInventoryDragDrawY, GetZ(spr));
        OldInventoryDragDrawX = dx;
        OldInventoryDragDrawY = dy;
        int target = OldInventoryDragTargetAt(army, x, y);
        if(target != OldInventoryDragTarget || !OldInventoryDragRefresh ||
           GetTime()-OldInventoryDragRefresh >= 150 || released)
        {
            OldInventoryDragTarget = target;
            OldInventoryDragRefresh = GetTime();
            OldInventoryDragAllowed = 0;
            if(target == 2097152)
                OldInventoryDragAllowed = SendCommandA(army, 312, OldStockInventoryLocator, 11) == 1;
            else if(target >= 0 && OldInventoryDragKind == 2)
                OldInventoryDragAllowed = SendCommandA(army, 343, OldInventoryDragQuote, OldInventoryDragPrice, target) == 1;
            else if(target >= 0)
                OldInventoryDragAllowed = SendCommandA(army, 341, OldStockInventoryLocator,
                    OldInventoryDragQuote, target) == 1;
        }
        int gamma = GammaEncodeToDword(90, -80, -80);
        if(OldInventoryDragAllowed) gamma = GammaEncodeToDword(-30, 70, -30);
        if(spr) Action(spr, ACT_SET_GAMMA, gamma);
    }
    if(released)
    {
        if(OldInventoryDragActive)
        {
            if(OldInventoryDragAllowed)
            {
                if(OldInventoryDragKind == 2)
                    OldShopLocalQueueResult = OldShopQueue(12, OldInventoryDragQuote, OldInventoryDragPrice, OldInventoryDragTarget);
                else if(OldInventoryDragTarget == 2097152)
                    OldShopLocalQueueResult = OldShopQueue(3, OldStockInventoryLocator, OldStockInventoryBase, OldStockInventoryQuantity);
                else OldShopLocalQueueResult = OldShopQueue(11, OldStockInventoryLocator, OldInventoryDragQuote, OldInventoryDragTarget);
                if(OldShopLocalQueueResult > 0) OldStockInventoryLocator = -1;
            }
            else if(OldInventoryDragTarget >= 0) OldShopLocalQueueResult = -6;
            OldStockInventoryClickTime = 0;
        }
        else if(OldInventoryDragTwice && OldShopVisible != 1)
        {
            if(SendCommandA(army, 312, OldStockInventoryLocator, 8) == 0) OldStockInventoryQueue(army, 6);
            else OldStockInventoryQueue(army, 7);
            OldStockInventoryClickTime = 0;
        }
        else OldStockInventoryClickTime = GetTime();
        OldInventoryDragCancel();
    }
}

OldInventoryDragShopArea(int x, int y) { return 0; }
'''
