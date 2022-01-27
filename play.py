from ppadb.client import Client as AdbClient
from PIL import Image
import copy
import time

def connect():
    global c, d
    c = AdbClient()
    d = c.devices()[0]
    

def saveImage():
    with open("img.png", "wb") as f:
        f.write(d.screencap())

grey = (188,188,188,255)


def img(savedColors=False):
    
    global l

    #grab image, get it in pixel by pixel form
    image = Image.open("img.png")
    l = list(image.getdata())

    nl = [l[i*1080:(i+1)*1080] for i in range(2400)]

    counts = []

    for r in nl:
        counts.append(r.count((188,188,188,255)))

    #grab each point where the barrier grey appears with nothing up & left, then skip to the next potential area
    points = []
    skip = 0
    for r in range(len(nl)):
        if skip:
            skip-=1
            continue
        for c in range(len(nl[0])):
            
            if counts[r] > 80 and nl[r][c] == grey and nl[r-1][c] != grey and nl[r][c-1] != grey:
                points.append((r,c))
                skip = 500


    vials = []
    #grab the colors in each vial
    for vial in points:
        r,c = vial
        colors = []
        for addR in range(4):
            colors.append(nl[100 + r + addR * 100][c+25])
        vials.append(colors)

    #remove all shades of grey (background)
    colors = []    
    for vial in vials:
        for color in vial:
            if color[0] != color[1] or color[1] != color[2]:
                colors.append(color)


    #create an interpretation to move from color to a number representing that color, but if we have a list already saved, make sure it's compatible (just additive)
    if savedColors:
        colorsList = savedColors
    else:
        colorsList = []
    for color in colors:
        if color not in colorsList:
            colorsList.append(color)

    #interpret each color
    #99 = blank
    #1XX = unknown, not XX
    #199 = totally unknown
    #2XX = formerly unknown, now known to be XX
    for v in range(len(vials)):
        for c in range(4):
            if vials[v][c] in colorsList:
                if vials[v][c] == (48, 50, 54, 255):
                    vials[v][c] = 100 + vials[v][c-1]
                    if 100 <= vials[v][c-1] < 200:
                        vials[v][c] = 199
                        
                else:
                    vials[v][c] = colorsList.index(vials[v][c])
            else:
                vials[v][c] = 99

    #print(colorsList)
    return [points,vials, colorsList]

def interpretImage(savedColors = False):
    i = img(savedColors)
    while img(savedColors) != i:
        i = img(savedColors)
    return i

def win(vials):
    for vial in vials:
        for color in range(1,len(vial)):
            if vial[color-1]%200 != vial[color]%200:
                return False
    return True

def top(vial):
    i = 0
    while vial[i] == 99 and i < 3:
        i+=1
    return vial[i]

def full(vial):
    return vial[0] != 99

def single(vial):
    for i in range(1,4):
        if vial[i-1] != 99 and vial[i-1]%200 != vial[i]%200:
            return False
    return True

def empty(vial):
    return vial[3] == 99

def secondTopCheck(vial):
    t = top(vial)
    t %= 200
    
    i = 0
    while i < 4 and (vial[i] == 99 or vial[i]% 200 == t):
        i+=1
    if i == 4:
        return False
    #i is the last position not known to be the same as the top
    #if it's unknown, we can only keep going if it can't be i (it's i + 100)
    #but if it's not unknown, behavior is fully defined, so we can keep going
    if 100<vial[i] <200:
        return vial[i] - 100 != t
    return False


def sortMoves(vials, moves):
    #prioritize moves that allow for consolidation later, then moves that will lead to a reveal
    
    frontMoves = []
    midMoves = []
    endMoves = []
    for move in moves:
        possibleCombos = [top(vials[m[0]])%200 for m in moves if m != move and m[1] == move[1]]
        if top(vials[move[0]])%200 in possibleCombos:
            frontMoves.append(move)
        elif hasUnknown([vials[move[0]]]):
            midMoves.append(move)
        else:
            endMoves.append(move)
    return frontMoves + midMoves +endMoves

def findDepth(vial):
    i = 0
    while i < 4 and vial[i] == 99:
        i +=1
    if i == 4:
        return 0
    depth = 0
    while i+depth < 4 and vial[i+depth] % 200 == vial[i] % 200:
        depth +=1
    return depth

def room(vial):
    i = 0
    while i < 4 and vial[i] == 99:
        i += 1
    return i

def moves(vials):
    
    possibles = []
    for vial in range(len(vials)):

        
        t = top(vials[vial]) % 200

        
        if 98 < t < 200:
            continue

        #if we don't know for sure that the second from the top isn't the same
        #color as this, we can't move
        if secondTopCheck(vials[vial]):
            continue

        isSingle = single(vials[vial])

        depth = findDepth(vials[vial])
        
        for otherVial in range(len(vials)):
            if room(vials[otherVial]) < depth:
                continue
            
            if isSingle and empty(vials[otherVial]):
                continue
            if vial == otherVial:
                continue
            t2 = top(vials[otherVial]) % 200
            if not full(vials[otherVial]) and (t2 == 99 or t2 == t):
                possibles.append((vial, otherVial))
    return sortMoves(vials, possibles)

def makeMove(vials, move):
    m1, m2 = move
    i1 = 0
    while vials[m1][i1] == 99:
        i1+=1
    
    count = 0
    newI = i1
    while newI < 4 and vials[m1][newI] == vials[m1][i1]:
        count += 1
        newI += 1
    
    i2= 0
    while i2 <4 and vials[m2][i2] == 99:
        i2+= 1
    i2 -=1

    v = copy.deepcopy(vials)

    #when moving a thing, the things under it are exposed, and so should no longer be 200 level
    value = 0
    #print(i1+count+value)
    for i in range(len(v[m1])):
        v[m1][i] %=200
    
    for offset in range(count):
        if offset > i2:
            break
        v[m2][i2 - offset] = v[m1][i1+offset] % 200
        v[m1][i1+offset] = 99

    
    return v

def solve(vials, moveList, maxDepth = 999):
    if maxDepth == 999:
        print("top layer")
    #print(vials)
    #print(preventations)
    if win(vials):
        return moveList
    
    if maxDepth == 0:
        return False
    

    
    for move in moves(vials):
        #print(move)
        v = makeMove(vials, move)
        s= solve(v,moveList + [move], maxDepth-1)
        if s:
            return s
        
    return False

def findRevealedLocations(vials):
    locs = []
    for vial in range(len(vials)):
        if 100 <= top(vials[vial]) < 200:
            locs.append(vial)
    return locs


def revealMax(vials, moveList, maxDepth = 999):
    
    #print(vials)
    #print(preventations)
    if maxDepth < 0:
        #print("returning empty")
        return [[],[]]

    revealed = findRevealedLocations(vials)
    saveMoveL = moveList
    
    for move in moves(vials):
        if maxDepth> 997:
            print(f"searching {maxDepth} with {move}")
        v = makeMove(vials, move)
        moveL, newReveals = revealMax(v,moveList + [move], maxDepth - 1)
        
        if len(newReveals) > len(revealed) or (len(newReveals) == len(revealed) and len(moveL) < len(saveMoveL)):
            revealed = newReveals
            saveMoveL = moveL
            if len(revealed) >= leftToReveal:
                #print(f"found movelist of {[saveMoveL, revealed]=}")
                return [saveMoveL, revealed]
    return [saveMoveL, revealed]


def executeMoves(points, moves):
    for move in moves:
        p1 = points[move[0]]
        p2 = points[move[1]]
        d.input_tap(p1[1], p1[0])
        time.sleep(.01)
        d.input_tap(p2[1],p2[0])
        time.sleep(2)




def solveNotMod5():
    saveImage()
    p,v, colors = interpretImage()
    moves = solve(v,[])
    executeMoves(p, moves)

    d.input_tap(290, 1444)
    time.sleep(1)
    
    d.input_tap(500, 1800)
    time.sleep(1)

def hasUnknown(vials):
    for vial in vials:
        for color in vial:
            if 99<color < 200:
                return True
    return False

def transpose(v, newV, revealed):
    transposeKnown(v, newV)
    
    for vial in revealed:
        i = 0
        newVial = newV[vial]
        try:
            while newVial[i] == 99:
                i += 1
        except:
            print(v)
            print(newV)
            print(revealed)
            print(vial)
            quit()

        while i < 4:
            if 99 < v[vial][i] < 200:
                if 99 < newVial[i] < 200:
                    v[vial][i] = newVial[i]
                else:
                    v[vial][i] = 200 + newVial[i]%200
                    
            i+=1
    return v

def setToReveal(v):
    total= 0
    for vial in v:
        for n in vial:
            if 99 < n < 200:
                total += 1
                break
    global leftToReveal
    leftToReveal = 1
    print(f"{leftToReveal=}")

#copy over all already known information that newV doesn't necessarily have to it
def transposeKnown(v, newV):
    for vial in range(len(newV)):
        for color in range(len(newV[0])):
            if 99 < newV[vial][color] < 200:
                if v[vial][color] != 199:
                    
                    newV[vial][color] = v[vial][color]


            
def solveMod5():
    
    saveImage()
    p,v, saveColors = interpretImage()
    while hasUnknown(v):
        print(f"{v=}")
        setToReveal(v)
        
        moves, revealed = revealMax(v,[])
        print(f"{moves=}")
        print(f"{revealed=}")
        executeMoves(p, moves)
        
        saveImage()
        p, newV, saveColors = interpretImage(saveColors)
        v = transpose(v, newV, revealed)
        transposeKnown(v,newV)
        while True:
            setToReveal(newV)
        
            moves, revealed = revealMax(newV,[], 15)
            print(f"{moves=}")
            print(f"{revealed=}")
            
            if len(revealed) == 0:
                print("breaking!")
                print(moves)
                print(revealed)
                break
            
            executeMoves(p, moves)
            time.sleep(2)
            saveImage()
            p, newV, saveColors = interpretImage(saveColors)
            v = transpose(v, newV, revealed)
        print("trying to solve")
        #THIS FAILS
        
        if(not hasUnknown(v)):
            if solve(newV,  []):
                moves = solve(newV, [])
                executeMoves(p, moves)
                break
        print("solve failed")
        print(v)
        d.input_tap(350, 200)
        time.sleep(1)
    else:
        moves = solve(v, [])
        executeMoves(p, moves)

    d.input_tap(290, 1444)
    time.sleep(1)
    
    d.input_tap(500, 1800)
    time.sleep(1)


    
        
        
connect()
level =int(input("current level: "))
while True:
    if level % 5 != 0:
        print("running not mod 5")
        try:
            solveNotMod5()
        except Exception as E:
            print("not mod 5 failed. Trying again")
            time.sleep(3)
            d.input_tap(350, 200)
            time.sleep(1)
            solveNotMod5()
    else:
        try:
            solveMod5()
        except Exception as E:
            print("mod 5 failed. Trying again")
            time.sleep(3)
            d.input_tap(350, 200)
            time.sleep(1)
            solveMod5()
    time.sleep(4)
    level+=1
    print(f"starting level: {level}")

#UNKNOWNS DON'T MOVE

#500, 1800
