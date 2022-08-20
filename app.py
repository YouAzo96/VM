import re
from browser import document, html, timer
virtualM = {
    "00000": "A",
    "00001": "B",
    "00010": "C",
    "00011": "D",
    "00100": "E",
    "00101": "F",
    "00110": "G",
    "00111": "H",
    "01000": "I",
    "01001": "J",
    "01010": "K",
    "01011": "L",
    "01100": "M",
    "01101": "N",
    "01110": "O",
    "01111": "P",
    "10000": "Q",
    "10001": "R",
    "10010": "S",
    "10011": "T",
    "10100": "U",
    "10101": "V",
    "10110": "W",
    "10111": "X",
    "11000": "Y",
    "11001": "Z",
    "11010": "1",
    "11011": "2",
    "11100": "3",
    "11101": "4",
    "11110": "5",
    "11111": "6",
}
# "VPageNum":"V|frameNum"
tlb = {}
# "frame#":"Byte data"
memo = {}
# "page num":"V|Frame Num" , take the first bit of the value as valid bit
ptable = {}
# "index":"V|Tag|Byte1|Byte0"
cache = {}


vmElem = document['vmemo']
memoElem = document['memo']
ptableElem = document["ptable"]
tlbElem = document["tlb"]
cacheElem = document["cache"]
vAddr = document["vaddr"]
err = document["error"]
cerr = document["cacheerr"]
tlberr = document["tlberr"]
pterr = document["pterr"]
sentdata = document["sentdata"]
sel = html.SELECT(size=1, multiple=False)


dropdown = document["drop"]

virtualAddr = None
physicalAddr = None
vPageNum = None
pageOffset = None
latestUpdatedFrame = -1
endianness = 0


def click(ev):
    erase()
    virtualAddr = vAddr.value
    if (nonzero_binary_re(virtualAddr) is False) or (len(virtualAddr) < 5):
        err.text = "Please enter a valid virtual address of 5 bits"

    else:
        vPageNum = virtualAddr[:3]
        pageOffset = virtualAddr[3:]
        # if page not in page table or the valid bit is 0
        if (vPageNum not in tlb):
            tlberr.text = "TLB Miss"
            if (vPageNum not in ptable) or (ptable[vPageNum][0] == "0"):
                pterr.text = "Page Fault"
                movePageToMemo(vPageNum)
                rePaint()
                ptable[vPageNum] = "1"+getbinary(latestUpdatedFrame, 2)
                tlb[vPageNum] = "1"+getbinary(latestUpdatedFrame, 2)
                updateTlb()
                # cache ops
                physicalAddr = getbinary(latestUpdatedFrame, 2) + pageOffset
                cacheIndex = physicalAddr[1:3]
                tag = physicalAddr[:1]
                byteOffset = physicalAddr[3:]
                cacheOperations(cacheIndex, tag, byteOffset)

            else:
                pterr.text = "Page Table Hit"

                # cache ops
                physicalAddr = ptable[vPageNum][1:] + pageOffset
                cacheIndex = physicalAddr[1:3]
                tag = physicalAddr[:1]
                byteOffset = physicalAddr[3:]
                cacheOperations(cacheIndex, tag, byteOffset)

        else:
            # cache ops
            tlberr.text = "TLB Hit"
            physicalAddr = ptable[vPageNum][1:] + pageOffset
            cacheIndex = physicalAddr[1:3]
            tag = physicalAddr[:1]
            byteOffset = physicalAddr[3]
            cacheOperations(cacheIndex, tag, byteOffset)


def cacheOperations(cacheIndex, tag, byteOffset):
    # if data not in cache
    if not isInCache(cacheIndex, tag):
        cerr.text = "Cache Miss"
        frameSeenBycache = tag + cacheIndex
        moveFrameToCache(frameSeenBycache)
        rePaint()
        p = html.P()
        if endianness == 0:
            p.text = cache[cacheIndex][2:][0 if byteOffset == 1 else 1]
        else:
            p.text = cache[cacheIndex][2:][int(byteOffset)]
        sentdata <= p
        # rePaint()
    else:
        cerr.text = "Cache Hit"
        p = html.P()

        if endianness == 0:
            p.text = cache[cacheIndex][2:][0 if (
                int(byteOffset) == 1) else 1]
        else:
            p.text = cache[cacheIndex][2:][int(byteOffset)]
        sentdata <= p
        # rePaint()


def isInCache(index, tag):
    if index in cache:
        # if Valid bit is 1 AND the tag matches the tag in our address
        if (cache[index][:1] == "1") and (cache[index][1:2] == tag):
            return True
        if (cache[index][:1] == "1") and (cache[index][1:2] != tag):
            cache[index][:1] == "0"
            return False
    return False


def moveFrameToCache(frameToCache):
    index = frameToCache[1:]
    tag = frameToCache[:1]
    if endianness == 0:
        data = memo[frameToCache+"1"]+memo[frameToCache+"0"]
    else:
        data = memo[frameToCache+"0"]+memo[frameToCache+"1"]
    cache[index] = "1"+tag+data  # V|Tag|B1|B0


def clear(ev):
    global memo, ptable, tlb, cache, sentdata, latestUpdatedFrame, endianness, pageOffset, vPageNum, physicalAddr, virtualAddr
    memo = {}
    ptable = {}
    tlb = {}
    cache = {}
    virtualAddr = None
    physicalAddr = None
    vPageNum = None
    pageOffset = None
    latestUpdatedFrame = -1
    endianness = 0
    # remove all elements from document
    for elem in document["vmemo"].childNodes:
        elem.remove()
    for elem in document["ptable"].childNodes:
        elem.remove()
    for elem in document["memo"].childNodes:
        elem.remove()
    for elem in document["tlb"].childNodes:
        elem.remove()
    for elem in document["cache"].childNodes:
        elem.remove()
    for i, elem in enumerate(sel.childNodes):
        if i < 2:
            elem.remove()
    err.text = ""
    tlberr.text = ""
    pterr.text = ""
    cerr.text = ""
    sentdata.text = ""
    initiate()


def erase():
    global err, tlberr, pterr, cerr
    err.text = ""
    tlberr.text = ""
    pterr.text = ""
    cerr.text = ""


def rePaint():
    # remove all elements from document
    for elem in document["vmemo"].childNodes:
        elem.remove()
    for elem in document["ptable"].childNodes:
        elem.remove()
    for elem in document["memo"].childNodes:
        elem.remove()
    for elem in document["tlb"].childNodes:
        elem.remove()
    for elem in document["cache"].childNodes:
        elem.remove()
    for i, elem in enumerate(sel.childNodes):
        if i < 2:
            elem.remove()
    initiate()


def keyup(ev):
    if ev.currentTarget.id == "vaddr":
        if (not nonzero_binary_re(vAddr.value)) or (len(vAddr.value) > 5):
            vAddr.value = vAddr.value[:len(vAddr.value)-1]
    if (len(vAddr.value) > 5):
        vAddr.value = vAddr.value[:5]


document["vaddr"].bind("keyup", keyup)
document["submit"].bind("click", click)
document["clear"].bind("click", clear)


def getbinary(x, n): return format(x, 'b').zfill(n)


def nonzero_binary_re(b):
    return re.match(r"^[01]+$", b) is not None


def drop_change(ev):
    selected = [option.value for option in sel if option.selected]
    global endianness
    endianness = selected[0]


sel.bind("change", drop_change)


def updateTlb():
    tlbkeys = list(tlb)
    lasttwo = {}
    if len(tlbkeys) >= 2:
        lasttwo[""+tlbkeys[len(tlbkeys)-1]] = tlb[""+tlbkeys[len(tlbkeys)-1]]
        lasttwo[""+tlbkeys[len(tlbkeys)-2]] = tlb[""+tlbkeys[len(tlbkeys)-2]]
    elif len(tlbkeys) > 0:
        lasttwo[""+tlbkeys[len(tlbkeys)-1]] = tlb[""+tlbkeys[len(tlbkeys)-1]]

    tlb.clear()
    for elem in reversed(list(lasttwo.keys())):
        tlb[elem] = lasttwo[elem]


def movePageToMemo(pageNum):
    global latestUpdatedFrame
    latestUpdatedFrame = (latestUpdatedFrame +
                          1) if (latestUpdatedFrame < 3 and latestUpdatedFrame >= 0) else 0
    for i in range(4):
        memo[getbinary(latestUpdatedFrame, 2)+getbinary(i, 2)
             ] = virtualM[pageNum+getbinary(i, 2)]
    # set any other valid bits for this frame to invalid in page table
    for elem in ptable:
        if (elem != pageNum) and (ptable[elem][1:] == getbinary(latestUpdatedFrame, 2)):
            ptable[elem] = "0"+ptable[elem][1:]  # set valid bit to zero


def initiate():
    choices = ["Big-Endian", "Little-Endian"]
    for i, item in enumerate(choices):
        opt = html.OPTION(item)
        opt.value = i
        if opt.value == endianness:
            opt.selected = True
        sel <= opt

    for byt in virtualM:
        row = html.TR()
        row <= html.TD(byt) + html.TD(virtualM[byt])
        vmElem <= row

    for i in range(16):
        row = html.TR()
        addr = getbinary(i, 4)
        td = html.TD()
        td.attrs["style"] = "width: 25px;height:10px"
        if addr in memo:
            row <= html.TD(addr) + html.TD(memo[addr])
        else:
            row <= html.TD(addr) + td
        memoElem <= row
    # only show the last two elems of TLB
    # and delete the rest everytime we repaint.
    i = 0

    td0 = html.TD()
    td0.text = "V"
    td = html.TD()
    td.text = "Page"
    td1 = html.TD()
    td1.text = "Frame"

    tlbElem <= td0
    tlbElem <= td
    tlbElem <= td1

    for elem in tlb:
        row = html.TR()
        row <= html.TD(tlb[elem][:1]) + html.TD(elem) + html.TD(tlb[elem][1:])
        tlbElem <= row
        i += 1

    for j in range(i, 2):
        row = html.TR()
        td = html.TD()
        td.attrs["style"] = "width: 25px;height:15px"
        td1 = html.TD("")
        td1.attrs["style"] = "width: 25px;height:15px"
        td2 = html.TD("")
        td2.attrs["style"] = "width: 25px;height:15px"
        row <= td + td1 + td2
        tlbElem <= row

    td0 = html.TD()
    td = html.TD()
    td.text = "Valid Bit"
    td1 = html.TD()
    td1.text = "Frame Number"

    ptableElem <= td0
    ptableElem <= td
    ptableElem <= td1

    for i in range(8):
        row = html.TR()
        addr = getbinary(i, 3)
        if addr in ptable:
            row <= html.TD(addr) + \
                html.TD(ptable[addr][:1]) + html.TD(ptable[addr][1:])
        else:
            row <= html.TD(addr) + html.TD("0") + html.TD("")

        ptableElem <= row

    td0 = html.TD()
    td = html.TD()
    td.text = "Valid Bit"
    td1 = html.TD()
    td1.text = "Tag"
    td2 = html.TD()
    td2.text = "Byte1"
    td3 = html.TD()
    td3.text = "Byte0"

    cacheElem <= td0
    cacheElem <= td
    cacheElem <= td1
    cacheElem <= td2
    cacheElem <= td3
    for i in range(4):
        row = html.TR()
        td = html.TD()
        index = getbinary(i, 2)
        if index in cache:
            row <= html.TD(index) + html.TD(cache[index][:1]) +\
                html.TD(cache[index][1:2]) + html.TD(cache[index]
                                                     [2:3]) + html.TD(cache[index][3:4])
        else:
            td.attrs["style"] = "width: 25px;height:10px"
            td1 = html.TD("")
            td1.attrs["style"] = "width: 25px;height:10px"
            td2 = html.TD("")
            td2.attrs["style"] = "width: 25px;height:10px"
            row <= html.TD(index) + html.TD("0") + td + td1 + td2

        cacheElem <= row

    dropdown = document["drop"]
    dropdown <= sel


initiate()
