.open "pbpx_952.01",0x163f000
.ps2

.org 0x17c97b8
@fontToRAM:

.org 0x17c98bc
@fontFromRAM:

.org 0x17ad7a8
@copyMenuFont:

.org 0x17ad84c
@renderMenuFonts:

.org 0x17c9928
@renderScreenFonts:

.org 0x17ade18
@menuFontStart:

.org 0x17ad8f0
@lampFontStart:

.org 0x17add68
@menuFontLoop:

.org 0x17ad730
@startMenuFontRender:

.org 0x197c4d0
@tableWidthOffset:

.org 0x197c060
@cache:

.org 0x197c06c
@oddBit:

.org 0x197c070

;obtain the correct font width
calculateFontWidth:
addiu s0, -0x2
lbu t2, (s0)
addiu s0, 0x1
lbu t1, (s0)
addiu t2, t2, -0xa1
addiu t1, t1, -0xa1
li t6, 0x5e
mult t2, t2, t6
add t1, t2, t1
li t6, 0x11a
slt t2, t1, t6
bnez t2, @@characterInRange
nop
li t1, 0x0
@@characterInRange:
li t0, @tableWidthOffset
add t0, t1
lbu t1, (t0)
bnez t1, @@hasWidth
nop
dmove t1, zero
li t1, 0x18
@@hasWidth:
li t2, 0x2
dmove t6, t1
div t1, t2
mflo t1
mfhi t0
add t7, t1, t0
add s1, t7
addiu s0, 0x1
li t2, @oddBit
lh t1, (t2)
xor t1, t1, t0
sh t1, 0x2(t2)
dmove t0, a0
dmove t1, a1
dmove t2, v1
jr ra
nop

;render font widths
setDialogFontWidth:
dmove t5, zero
li t5, @cache
sd ra, (t5)
dmove v1, s1
dmove a1, s0
lw s0, 0x8(t5)
dmove s1, zero
jal calculateFontWidth
nop
dmove t0, zero
dmove t1, zero
dmove t2, zero
dmove s0, a1
ld ra, (t5)
nop
dmove s1, v1
dmove v1, zero
jr ra
nop

;render correct offsets for normal dialog
setScreenTextOffsets:
dmove t5, zero
li t5, @cache
sd ra, (t5)
jal updateOddBit
nop
add v0, s1
ld ra, (t5)
sw v0, 0x40(s0)
jr ra
nop

;render correct widths for normal dialog
setDialogOffsets:
dmove t5, zero
li t5, @cache
lw t7, 0x38(s0)
nop
sw t7, 0x8(t5)
dmove t7, ra
jal @fontToRAM
dmove ra, t7
jr ra
nop

;save correct address for widths
cacheWidthAddresses:
lbu v1, (s0)
addiu s0, 0x1
li t5, @cache
sw s0, 0x8(t5)
addiu s0, -0x1
jr ra
nop

;center text
;v0 = number of characters
;a0 = final width of entire text on the current line
;0x38(s0) =  start of the text to be considered
;do not count a1a1 or 20; the game doesn't, so we don't either
centerDialogText:
lw t5, 0x38(s0)
addiu t5, -0x1
li t7, 0x20
dmove a0, zero
dmove a1, zero
@@loopstart:
beq a1, v0, @@loopend
nop
addiu t5, 0x1
lbu t2, (t5)
addiu t5, 0x1
lbu t1, (t5)
beql t2, t7, @@loopstart
nop
addiu t6, t2, -0xa1
li t0, 0x5e
mult t6, t6, t0
addiu t0, t1, -0xa1
add t0, t6
sll t2, t2, 0x08
or t1, t1, t2
li t7, 0xa1a1
beql t1, t7, @@loopstart
addiu a1, 0x1
li t6, 0x11a
slt t2, t0, t6
bnez t2, @@characterInRange
nop
li t0, 0x0
@@characterInRange:
li t1, @tableWidthOffset
add t1, t0
lbu t0, (t1)
bnez t0, @@hasWidth
nop
dmove t0, zero
li t0, 0x18
@@hasWidth:
add a0, t0
addiu a1, 0x1
bne a1, v0, @@loopstart
nop
@@loopend:
li t0, 0x2
div a0, t0
mflo a1
mfhi t2
add a1, t2
div a1, t0
mflo v1
jr ra
nop

;set correct widths for menu text
setMenuTextWidth:
addiu t0, v0, -0xa1
andi t1, a1, 0xff
addiu t1, -0xa1
li t6, 0x5e
mult t0, t0, t6
add t1, t0, t1
li t6, 0x11a
slt t2, t1, t6
bnez t2, @@characterInRange
nop
li t1, 0x0
@@characterInRange:
li t0, @tableWidthOffset
add t0, t1
lbu t7, (t0)
dmove t6, t7
li t2, 0x2
div t6, t2
mflo t1
mfhi t0
add t7, t1, t0
li t2, @oddBit
lh t1, (t2)
xor t1, t1, t0
sh t1, 0x2(t2)
li v1, 0xd380
j @startMenuFontRender
nop

;get correct line width for centering menu text
calculateLineWidth:
addiu t0, v1, -0xa1
addiu t7, v0, -0xa1
li t6, 0x5e
mult t0, t0, t6
add t7, t0, t7
li t6, 0x11a
slt t0, t7, t6
bnez t0, @@characterInRange
nop
li t7, 0x0
@@characterInRange:
li t0, @tableWidthOffset
add t0, t7
lbu t7, (t0)
add a3, t7
j @renderMenuFonts
nop

resetOddBit:
lw a3, 0x38(s0)
lbu v1, (a3)
beqz v1, @@reset
nop
li t0, 0xa
bne v1, t0, @@noReset
nop
@@reset:
li t0, @oddBit
sh zero, (t0)
@@noReset:
jr ra
nop

cleanupOddBit:
li a0, @oddBit
sh zero, (a0)
lw a0, 0x48(s0)
jr ra
nop

resetMenuOddBit:
li v0, @oddBit
sh zero, (v0)
addiu v0, a2, 0x1
li v1, 0x20
jr ra
nop

resetScreenOddBit:
li t2, @oddBit
sh zero, (t2)
j @renderScreenFonts
nop

;update even/odd widths for menus
updateMenuOddBit:
add v0, t7
li t0, @oddBit
lh t3, (t0)
lh t1, 0x2(t0)
sh t1, (t0)
li t0, 0x2
div t6, t0
mfhi t0
and t0, t3
sub v0, t0
j @menuFontLoop
nop

;update even/odd widths
updateOddBit:
add s1, t7
li t2, @oddBit
lh t3, (t2)
lh t1, 0x2(t2)
sh t1, (t2)
li t2, 0x2
div t6, t2
mfhi t2
and t2, t3
sub s1, t2
jr ra
nop

;handle even/odd widths
handleOddWidths:
li t3, @oddBit
nop
lh s3, (t3)
nop
beqz s3, @@saveByte
lbu s3, -0x1(a2)
nop
sll s3, 0x04
srl s3, 0x04
sll t3, a0, 0x04
or s3, t3
sb s3, -0x1(a2)
srl a0, 0x04
@@saveByte:
sb a0, (a2)
li t3, -0x10
j @fontFromRAM
nop

handleOddMenuWidths:
li t4, @oddBit
nop
lh v1, (t4)
nop
beqz v1, @@evenByte
lbu v1, -0x1(a2)
nop
sll v1, 0x04
srl v1, 0x04
andi v0, 0xff
sll t4, v0, 0x04
or v1, t4
sb v1, -0x1(a2)
srl a0, v0, 0x04
b @@finish
nop
@@evenByte:
dmove a0, v0
@@finish:
li t4, -0x10
j @copyMenuFont
nop

;offsets for save screens

.orga 0x18a978

jal updateOddBit
lbu v0, (s0)
add s2, t6

;rendering widths for dialogs and save screens

.orga 0x18a808

jal setDialogFontWidth

.orga 0x18a838

slt a0, a2, t7

.orga 0x18a8b0

slt v1, a3, t7

;offsets for dialogs and save screens

.orga 0x5554

jal setScreenTextOffsets

;widths for some dialogs

.orga 0x553c

jal setDialogOffsets

;offsets and widths for some dialogs

.orga 0x56c4

jal setDialogOffsets

;widths for dialogs

.orga 0x18a940

jal cacheWidthAddresses

;centering for dialogs

.orga 0x5458

jal centerDialogText
nop

;link menu text widths and offsets with vfr functions

.org 0x17ad72c

j setMenuTextWidth

.orga 0x16ed64

j updateMenuOddBit

.orga 0x16e790

slt a1, a3, t7

;link centering menu texts with vfr functions

.orga 0x16e848

j calculateLineWidth

.orga 0x170d98

nop

.orga 0x16ee7c

nop

.orga 0x176138

nop

.orga 0x17625c

nop

.orga 0x1773c4

nop

.orga 0x18a8b4

;odd numbered widths

nop
j handleOddWidths

.org 0x17adbb8

jal cleanupOddBit

.org 0x17ad7a4

j handleOddMenuWidths

.org 0x164440c

jal resetOddBit
nop

.org 0x17adcec

jal resetMenuOddBit
nop

.org 0x17c9924

j resetScreenOddBit

.Close
