#include "Vpulse_controller.h"
#include "verilated.h"
#include <iostream>

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vpulse_controller* top = new Vpulse_controller;

    top->clk = 0;
    top->rst_n = 0;
    top->target_phase_adj = 0x05A0; // Ajuste inicial desde la IA

    // Bucle de simulación de ciclos de reloj de la FPGA
    for (int i = 0; i < 10; i++) {
        top->rst_n = (i > 1) ? 1 : 0;
        top->clk = !top->clk;
        top->eval();
        
        std::cout << "[FPGA VIRTUAL | Ciclo " << i << "] DAC Out: 0x" 
                  << std::hex << top->microwave_dac_out 
                  << " | Ready: " << (int)top->pulse_ready << std::dec << std::endl;
    }

    delete top;
    return 0;
}
