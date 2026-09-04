# Script Tcl para Síntesis y Análisis de Tiempos Estáticos (STA)
read_verilog -sv pulse_controller.sv
read_verilog -sv pulse_controller_axi.sv

# Seleccionar tarjeta objetivo (Xilinx Zynq UltraScale+ ZCU102)
set_property part xczu9eg-ffvb1156-2-e [current_project]

# Definir Reloj Objetivo: 250 MHz (Periodo = 4.0 ns)
create_clock -name s_axi_aclk -period 4.000 [get_ports s_axi_aclk]

# Ejecutar Síntesis Lógica
synth_design -top pulse_controller_axi -flatten_hierarchy rebuilt

# Generar Reporte de Tiempos (Slack Check)
report_timing_summary -file timing_summary_250mhz.rpt -setup -hold
