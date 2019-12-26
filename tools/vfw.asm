.open "pbpx_952.01",0x1640000
.ps2
.orga 0x33d070

;obtain the correct font width
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
bnez t2, 0x197d0a8
nop
li t1, 0x0
li t0, 0x197c310 ;width table index
add t0, t1
lbu t1, (t0)
bnez t1, 0x197d0c8
nop
dmove t1, zero
li t1, 0x7
add s1, t1
addiu s0, 0x1
li t6, 0x2
mult t6, t6, t1
nop
dmove t0, a0
dmove t1, a1
dmove t2, v1
jr ra
nop

;render font widths
dmove t5, zero
li t5, 0x197c060
sd ra, (t5)
dmove v1, s1
dmove a1, s0
lw s0, 0x8(t5)
dmove s1, zero
jal 0x197c070
nop
dmove t0, zero
dmove t1, zero
dmove t2, zero
dmove s0, a1
ld ra, (t5)
dmove t6, s1
dmove s1, v1
dmove v1, zero
jr ra
nop

;render correct offsets for normal dialog
dmove t5, zero
li t5, 0x0197c060
sd ra, (t5)
dmove t7, s0
lw s0, 0x8(t5)
jal 0x197c070
nop
dmove s0, t7
add v0, s1
ld ra, (t5)
sw v0, 0x40(s0)
jr ra
nop

;render correct widths for normal dialog
dmove t5, zero
li t5, 0x0197c068
lw t7, 0x38(s0)
nop
sw t7, (t5)
dmove t7, ra
jal 0x17c97b8
dmove ra, t7
jr ra
nop

;save correct address for widths
lbu v1, (s0)
addiu s0, 0x1
li t5, 0x0197c068
sw s0, (t5)
addiu s0, -0x1
jr ra
nop

;center text
;v0 = number of characters
;a0 = final width of entire text on the current line
;0x38(s0) =  start of the text to be considered
;do not count a1a1 or 20; the game doesn't, so we don't either
lw t5, 0x38(s0)
addiu t5, -0x1
li t7, 0x20
dmove a0, zero
dmove a1, zero
beq a1, v0, 0x197d264 ;loop here
nop
addiu t5, 0x1
lbu t2, (t5)
addiu t5, 0x1
lbu t1, (t5)
beql t2, t7, 0x197d1d8 ;go back to the top
nop
addiu t6, t2, -0xa1
li t0, 0x5e
mult t6, t6, t0
addiu t0, t1, -0xa1
add t0, t6
sll t2, t2, 0x08
or t1, t1, t2
li t7, 0xa1a1
beql t1, t7, 0x197d1d8 ; go back to the top
addiu a1, 0x1
li t6, 0x11a
slt t2, t0, t6
bnez t2, 0x197d234
nop
li t0, 0x0
li t1, 0x197c310 ;width table index
add t1, t0
lbu t0, (t1)
bnez t0, 0x197d254
nop
dmove t0, zero
li t0, 0x7
add a0, t0
addiu a1, 0x1
bne a1, v0, 0x197d1d8 ;go back to the top
nop
li t0, 0x2
div a0, t0
mflo v1
jr ra
nop

;get correct widths for menu text
addiu t0, a1, -0xa1
addiu t1, a0, -0xa1
li t6, 0x5e
mult t0, t0, t6
add t1, t0, t1
li t6, 0x11a
slt t2, t1, t6
bnez t2, 0x197d2a0
nop
li t1, 0x0
li t0, 0x197c310 ;width table index
add t0, t1
lbu t7, (t0)
andi a1, v0, 0xffff
jr ra
nop

;get correct line width for centering menu text
addiu t0, v1, -0xa1
addiu t7, v0, -0xa1
li t6, 0x5e
mult t0, t0, t6
add t7, t0, t7
li t6, 0x11a
slt t0, t7, t6
bnez t0, 0x197d2e4
nop
li t7, 0x0
li t0, 0x197c310
add t0, t7
lbu t7, (t0)
li t0, 0x2
mult t7, t7, t0
add a3, t7
j 0x17ad84c
nop

;offsets for save screens

.orga 0x18a978

jal 0x197c070
lbu v0, (s0)
add s2, t6

;rendering widths for dialogs and save screens

.orga 0x18a808

jal 0x197c0f0

.orga 0x18a838

slt a0, a2, t6

.orga 0x18a8b0

slt v1, a3, t6

;offsets for dialogs and save screens

.orga 0x5554

jal 0x197c140

;widths for some dialogs

.orga 0x553c

jal 0x197c178

;offsets and widths for some dialogs

.orga 0x56c4

jal 0x197c174

;widths for dialogs

.orga 0x18a940

jal 0x197c1a4

;centering for dialogs

.orga 0x5458

jal 0x197c1c4
nop

;link menu text widths and offsets with vfr functions

.orga 0x16ed30

jal 0x197c278

.orga 0x16ed64

add v0,t7

.orga 0x16e790

slt a1, a3, t7

;link centering menu texts with vfr functions

.orga 0x16e848

j 0x197c2bc

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

.Close
