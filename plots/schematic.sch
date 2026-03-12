v {xschem version=3.4.5 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {SKY130 Two-Stage Miller OTA — NMOS input, cascode PMOS load} 50 -700 0 0 0.6 0.6 {}
T {Cascode load in first stage for higher gain and CMRR} 50 -660 0 0 0.4 0.4 {}
T {=== BIAS GENERATION ===} 50 -630 0 0 0.4 0.4 {}
T {PMOS bias mirror} 50 -600 0 0 0.4 0.4 {}
T {Cascode PMOS bias — diode-connected for gate voltage} 50 -570 0 0 0.4 0.4 {}
T {=== FIRST STAGE ===} 50 -540 0 0 0.4 0.4 {}
T {=== SECOND STAGE ===} 50 -510 0 0 0.4 0.4 {}
T {=== Miller compensation ===} 50 -480 0 0 0.4 0.4 {}
T {=== Load ===} 50 -450 0 0 0.4 0.4 {}
C {devices/vsource.sym} 80 -280 0 0 {name=Vdd
value=1.8}
C {devices/vsource.sym} 50 -70 0 0 {name=Vss
value=0}
C {devices/vsource.sym} 970 -290 0 0 {name=Vinp
value=0.9}
C {devices/vsource.sym} 820 -80 0 0 {name=Vinm
value=0.9}
C {devices/isource.sym} 1000 -40 0 0 {name=Ibias
value={Ibias}}
C {sky130_fd_pr/nfet_01v8.sym} 1190 10 0 0 {name=XMbn
W={Wbn}u
L={Lbn}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1680 -420 0 0 {name=XMbp1
W={Wbp}u
L={Lbp}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1450 -140 0 0 {name=XMbp2
W={Wbn}u
L={Lbn}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1290 180 0 0 {name=XMbc
W={Wc}u
L={Lc}u
nf=1
spiceprefix=X}
C {devices/isource.sym} 1090 160 0 0 {name=Ibcas
value={Ibias}}
C {sky130_fd_pr/nfet_01v8.sym} 1350 0 0 0 {name=XM5
W={W5}u
L={L5}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1100 -150 0 0 {name=XM1
W={W1}u
L={L1}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1190 -320 0 1 {name=XM2
W={W1}u
L={L1}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1370 -310 0 0 {name=XM3a
W={W3}u
L={L3}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1660 -220 0 0 {name=XM4a
W={W3}u
L={L3}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1300 -120 0 0 {name=XM3b
W={Wc}u
L={Lc}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1590 -40 0 0 {name=XM4b
W={Wc}u
L={Lc}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1520 -340 0 1 {name=XM6
W={W6}u
L={L6}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1530 100 0 0 {name=XM7
W={W7}u
L={L7}u
nf=1
spiceprefix=X}
C {devices/res.sym} 1850 -390 0 0 {name=Rc
value={Rc}}
C {devices/capa.sym} 1890 -180 0 0 {name=Cc
value={Cc}p}
C {devices/capa.sym} 1840 -20 0 0 {name=CL
value=5p}
N 970 -320 1210 -320 {lab=inp}
N 820 -110 1080 -110 {lab=inm}
N 1080 -110 1080 -150 {lab=inm}
N 1680 -450 1600 -450 {lab=biasp}
N 1600 -450 1600 -350 {lab=biasp}
N 1660 -420 1600 -420 {lab=biasp}
N 1600 -420 1600 -350 {lab=biasp}
N 1450 -170 1600 -170 {lab=biasp}
N 1600 -170 1600 -350 {lab=biasp}
N 1350 -30 1210 -30 {lab=tail}
N 1210 -30 1210 -150 {lab=tail}
N 1100 -120 1210 -120 {lab=tail}
N 1210 -120 1210 -150 {lab=tail}
N 1190 -290 1210 -290 {lab=tail}
N 1210 -290 1210 -150 {lab=tail}
N 1100 -180 1350 -180 {lab=n1}
N 1350 -180 1350 -220 {lab=n1}
N 1350 -310 1350 -220 {lab=n1}
N 1640 -220 1350 -220 {lab=n1}
N 1300 -150 1350 -150 {lab=n1}
N 1350 -150 1350 -220 {lab=n1}
N 1190 -350 1540 -350 {lab=n2}
N 1540 -350 1540 -300 {lab=n2}
N 1590 -70 1540 -70 {lab=n2}
N 1540 -70 1540 -300 {lab=n2}
N 1540 -340 1540 -300 {lab=n2}
N 1850 -420 1540 -420 {lab=n2}
N 1540 -420 1540 -300 {lab=n2}
N 1370 -340 1300 -340 {lab=p1}
N 1300 -340 1300 -90 {lab=p1}
N 1660 -250 1590 -250 {lab=p2}
N 1590 -250 1590 -10 {lab=p2}
N 1520 -370 1700 -370 {lab=out}
N 1700 -370 1700 -120 {lab=out}
N 1530 70 1700 70 {lab=out}
N 1700 70 1700 -120 {lab=out}
N 1890 -150 1700 -150 {lab=out}
N 1700 -150 1700 -120 {lab=out}
N 1840 -50 1700 -50 {lab=out}
N 1700 -50 1700 -120 {lab=out}
N 1850 -360 1890 -360 {lab=n2rc}
N 1890 -360 1890 -210 {lab=n2rc}
C {devices/vdd.sym} 80 -310 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1000 -70 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1680 -390 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1700 -420 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1290 210 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1310 180 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1370 -280 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1390 -310 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1660 -190 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1680 -220 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1320 -120 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1610 -40 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1520 -310 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1500 -340 0 0 {name=l_vdd lab=VDD}
C {devices/gnd.sym} 80 -250 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 50 -40 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 970 -260 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 820 -50 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 1840 10 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 50 -100 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1190 40 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1210 10 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1450 -110 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1470 -140 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1090 190 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1350 30 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1370 0 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1120 -150 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1170 -320 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1530 130 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1550 100 0 0 {name=l_vss lab=VSS}
C {devices/lab_pin.sym} 1000 -10 0 0 {name=l_biasn sig_type=std_logic lab=biasn}
C {devices/lab_pin.sym} 1190 -20 0 0 {name=l_biasn sig_type=std_logic lab=biasn}
C {devices/lab_pin.sym} 1170 10 0 0 {name=l_biasn sig_type=std_logic lab=biasn}
C {devices/lab_pin.sym} 1430 -140 0 0 {name=l_biasn sig_type=std_logic lab=biasn}
C {devices/lab_pin.sym} 1330 0 0 0 {name=l_biasn sig_type=std_logic lab=biasn}
C {devices/lab_pin.sym} 1510 100 0 0 {name=l_biasn sig_type=std_logic lab=biasn}
C {devices/lab_pin.sym} 1290 150 0 0 {name=l_pcas sig_type=std_logic lab=pcas}
C {devices/lab_pin.sym} 1270 180 0 0 {name=l_pcas sig_type=std_logic lab=pcas}
C {devices/lab_pin.sym} 1090 130 0 0 {name=l_pcas sig_type=std_logic lab=pcas}
C {devices/lab_pin.sym} 1280 -120 0 0 {name=l_pcas sig_type=std_logic lab=pcas}
C {devices/lab_pin.sym} 1570 -40 0 0 {name=l_pcas sig_type=std_logic lab=pcas}
