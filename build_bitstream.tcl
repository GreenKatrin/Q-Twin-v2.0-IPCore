# ==============================================================================
# SCRIPT DE SÍNTESIS, IMPLEMENTACIÓN Y BITSTREAM - Q-TWIN v2.0
# Target Hardware: AMD/Xilinx Zynq UltraScale+ ZCU102 (xczu9eg-ffvb1156-2-e)
# ==============================================================================

# 1. Creación del Proyecto
create_project -force qtwin_fpga_hw ./vivado_build -part xczu9eg-ffvb1156-2-e

# 2. Ingesta de Archivos RTL SystemVerilog
read_verilog -sv pulse_controller.sv
read_verilog -sv pulse_controller_axi.sv

# 3. Restricciones de Reloj (250 MHz / Periodo = 4.0 ns)
set clock_fd [open ./vivado_build/clocks.xdc w]
puts $clock_fd "create_clock -period 4.000 -name s_axi_aclk [get_ports s_axi_aclk]"
close $clock_fd
read_xdc ./vivado_build/clocks.xdc

# 4. Síntesis Lógica
puts "🔨 [VIVADO] Iniciando Síntesis Lógica para pulse_controller_axi..."
synth_design -top pulse_controller_axi -flatten_hierarchy rebuilt

# 5. Place & Route (Optimización de Tiempos)
puts "📌 [VIVADO] Ejecutando Placement y Routing..."
opt_design
place_design
route_design

# 6. Reportes de Verificación STA (Setup & Hold Slack)
report_timing_summary -file ./vivado_build/timing_summary_250mhz.rpt
report_utilization -file ./vivado_build/resource_utilization.rpt

# 7. Generación de Bitstream
puts "📦 [VIVADO] Generando archivo Bitstream .bit..."
write_bitstream -force ./vivado_build/pulse_controller_axi.bit
puts "✅ [VIVADO] Bitstream 'pulse_controller_axi.bit' generado exitosamente."
