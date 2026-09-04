`timescale 1ns / 1ps

module pulse_controller_tb;

    logic        clk;
    logic        rst_n;
    logic [15:0] phase_compensation_reg;
    logic [15:0] dac_microwave_out;
    logic        pulse_active;

    // Instancia del IP-Core Top-Level AXI
    pulse_controller_axi uut (
        .s_axi_aclk           (clk),
        .s_axi_aresetn        (rst_n),
        .phase_compensation_reg(phase_compensation_reg),
        .dac_microwave_out    (dac_microwave_out),
        .pulse_active         (pulse_active)
    );

    // Generador de reloj a 250 MHz (Periodo = 4 ns)
    always #2 clk = ~clk;

    initial begin
        // Archivo VCD para visualización en GTKWave
        $dumpfile("wave.vcd");
        $dumpvars(0, pulse_controller_tb);

        clk = 0;
        rst_n = 0;
        phase_compensation_reg = 16'h0000;

        #10;
        rst_n = 1;
        #10;

        // Estímulo 1: Inyección de Fase 0x05A0
        phase_compensation_reg = 16'h05A0;
        #20;

        // Estímulo 2: Inyección de Fase 0x10E0 desde Agente DRL
        phase_compensation_reg = 16'h10E0;
        #40;

        $display("✅ [TESTBENCH SUCCESS] Simulación completada. Archivo wave.vcd generado.");
        $finish;
    end

endmodule
