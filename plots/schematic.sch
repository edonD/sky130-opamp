v {xschem version=3.4.5 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {SKY130 Two-Stage Miller OTA — NMOS input, independent stage biasing} 50 -700 0 0 0.6 0.6 {}
T {Separate bias currents for first and second stage for optimal power allocation} 50 -660 0 0 0.4 0.4 {}
T {=== BIAS GENERATION — Stage 1 ===} 50 -630 0 0 0.4 0.4 {}
T {PMOS bias for second stage} 50 -600 0 0 0.4 0.4 {}
T {=== BIAS GENERATION — Stage 2 ===} 50 -570 0 0 0.4 0.4 {}
T {=== FIRST STAGE ===} 50 -540 0 0 0.4 0.4 {}
T {=== SECOND STAGE ===} 50 -510 0 0 0.4 0.4 {}
T {=== Miller compensation ===} 50 -480 0 0 0.4 0.4 {}
T {=== Load ===} 50 -450 0 0 0.4 0.4 {}
C {devices/vsource.sym} 40 -340 0 0 {name=Vdd
value=1.8}
C {devices/vsource.sym} 60 -130 0 0 {name=Vss
value=0}
C {devices/vsource.sym} 1020 -350 0 0 {name=Vinp
value=0.9}
C {devices/vsource.sym} 920 -190 0 0 {name=Vinm
value=0.9}
C {devices/isource.sym} 860 20 0 0 {name=Ibias1
value={Ibias1}}
C {sky130_fd_pr/nfet_01v8.sym} 990 130 0 0 {name=XMbn1
W={Wbn1}u
L={Lbn1}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1370 150 0 0 {name=XMbp1
W={Wbp}u
L={Lbp}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1190 90 0 0 {name=XMbp2
W={Wbn1}u
L={Lbn1}u
nf=1
spiceprefix=X}
C {devices/isource.sym} 1060 310 0 0 {name=Ibias2
value={Ibias2}}
C {sky130_fd_pr/nfet_01v8.sym} 1250 260 0 0 {name=XMbn2
W={Wbn2}u
L={Lbn2}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1060 -70 0 0 {name=XM5
W={W5}u
L={L5}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1230 -340 0 0 {name=XM1
W={W1}u
L={L1}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1370 -240 0 1 {name=XM2
W={W1}u
L={L1}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1510 -510 0 0 {name=XM3
W={W3}u
L={L3}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1500 -310 0 0 {name=XM4
W={W3}u
L={L3}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/pfet_01v8.sym} 1600 -170 0 1 {name=XM6
W={W6}u
L={L6}u
nf=1
spiceprefix=X}
C {sky130_fd_pr/nfet_01v8.sym} 1380 -20 0 1 {name=XM7
W={W7}u
L={L7}u
nf=1
spiceprefix=X}
C {devices/res.sym} 1700 -350 0 0 {name=Rc
value={Rc}}
C {devices/capa.sym} 1810 -200 0 0 {name=Cc
value={Cc}p}
C {devices/capa.sym} 1720 0 0 0 {name=CL
value=5p}
N 1020 -380 1390 -380 {lab=inp}
N 1390 -380 1390 -240 {lab=inp}
N 920 -220 1210 -220 {lab=inm}
N 1210 -220 1210 -340 {lab=inm}
N 1370 120 1300 120 {lab=biasp}
N 1300 120 1300 110 {lab=biasp}
N 1350 150 1300 150 {lab=biasp}
N 1300 150 1300 110 {lab=biasp}
N 1190 60 1300 60 {lab=biasp}
N 1300 60 1300 110 {lab=biasp}
N 1060 340 1240 340 {lab=bias2n}
N 1240 340 1240 200 {lab=bias2n}
N 1250 230 1240 230 {lab=bias2n}
N 1240 230 1240 200 {lab=bias2n}
N 1230 260 1240 260 {lab=bias2n}
N 1240 260 1240 200 {lab=bias2n}
N 1400 -20 1240 -20 {lab=bias2n}
N 1240 -20 1240 200 {lab=bias2n}
N 1060 -100 1220 -100 {lab=tail}
N 1220 -100 1220 -210 {lab=tail}
N 1230 -310 1220 -310 {lab=tail}
N 1220 -310 1220 -210 {lab=tail}
N 1370 -210 1220 -210 {lab=tail}
N 1230 -370 1430 -370 {lab=n1}
N 1430 -370 1430 -430 {lab=n1}
N 1510 -540 1430 -540 {lab=n1}
N 1430 -540 1430 -430 {lab=n1}
N 1490 -510 1430 -510 {lab=n1}
N 1430 -510 1430 -430 {lab=n1}
N 1480 -310 1430 -310 {lab=n1}
N 1430 -310 1430 -430 {lab=n1}
N 1370 -270 1550 -270 {lab=n2}
N 1550 -270 1550 -290 {lab=n2}
N 1500 -340 1550 -340 {lab=n2}
N 1550 -340 1550 -290 {lab=n2}
N 1620 -170 1550 -170 {lab=n2}
N 1550 -170 1550 -290 {lab=n2}
N 1700 -380 1550 -380 {lab=n2}
N 1550 -380 1550 -290 {lab=n2}
N 1600 -200 1630 -200 {lab=out}
N 1630 -200 1630 -110 {lab=out}
N 1380 -50 1630 -50 {lab=out}
N 1630 -50 1630 -110 {lab=out}
N 1810 -170 1630 -170 {lab=out}
N 1630 -170 1630 -110 {lab=out}
N 1720 -30 1630 -30 {lab=out}
N 1630 -30 1630 -110 {lab=out}
N 1700 -320 1810 -320 {lab=n2rc}
N 1810 -320 1810 -230 {lab=n2rc}
C {devices/vdd.sym} 40 -370 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 860 -10 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1370 180 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1390 150 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1060 280 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1510 -480 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1530 -510 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1500 -280 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1520 -310 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1600 -140 0 0 {name=l_vdd lab=VDD}
C {devices/vdd.sym} 1580 -170 0 0 {name=l_vdd lab=VDD}
C {devices/gnd.sym} 40 -310 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 60 -100 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 1020 -320 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 920 -160 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 1720 30 0 0 {name=l_0 lab=GND}
C {devices/gnd.sym} 60 -160 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 990 160 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1010 130 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1190 120 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1210 90 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1250 290 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1270 260 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1060 -40 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1080 -70 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1250 -340 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1350 -240 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1380 10 0 0 {name=l_vss lab=VSS}
C {devices/gnd.sym} 1360 -20 0 0 {name=l_vss lab=VSS}
C {devices/lab_pin.sym} 860 50 0 0 {name=l_bias1n sig_type=std_logic lab=bias1n}
C {devices/lab_pin.sym} 990 100 0 0 {name=l_bias1n sig_type=std_logic lab=bias1n}
C {devices/lab_pin.sym} 970 130 0 0 {name=l_bias1n sig_type=std_logic lab=bias1n}
C {devices/lab_pin.sym} 1170 90 0 0 {name=l_bias1n sig_type=std_logic lab=bias1n}
C {devices/lab_pin.sym} 1040 -70 0 0 {name=l_bias1n sig_type=std_logic lab=bias1n}
