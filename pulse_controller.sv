module pulse_controller (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [15:0] target_phase_adj,
    output logic [15:0] microwave_dac_out,
    output logic        pulse_ready
);

    logic [15:0] phase_accumulator;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase_accumulator <= 16'h0000;
            microwave_dac_out <= 16'h0000;
            pulse_ready       <= 1'b0;
        end else begin
            phase_accumulator <= phase_accumulator + target_phase_adj;
            microwave_dac_out <= phase_accumulator;
            pulse_ready       <= 1'b1;
        end
    end

endmodule
