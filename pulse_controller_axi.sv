// Módulo Top-Level Sintetizable con Interfaz AXI4-Lite
module pulse_controller_axi #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 4
)(
    input  logic        s_axi_aclk,
    input  logic        s_axi_aresetn,
    // Interfaz simplificada AXI4-Lite para registro de control
    input  logic [15:0] phase_compensation_reg,
    output logic [15:0] dac_microwave_out,
    output logic        pulse_active
);

    // Módulo de control de fase interno
    pulse_controller core_inst (
        .clk              (s_axi_aclk),
        .rst_n            (s_axi_aresetn),
        .target_phase_adj (phase_compensation_reg),
        .microwave_dac_out(dac_microwave_out),
        .pulse_ready      (pulse_active)
    );

endmodule
