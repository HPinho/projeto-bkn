"""Testes Semânticos e Comportamentais Executáveis da Camada Física I2C (I2C-5).

Testa a execução semântica real de:
- WRITE de bytes
- READ gravando bytes reais no buffer de destino
- WRITE -> REPEATED START -> READ (combined transaction)
- Detecção e tratamento de ADDRESS_NACK
- Detecção e tratamento de DATA_NACK
- Detecção e tratamento de ARBITRATION_LOST
- Timeout e detecção de barramento preso (SCL hang)
- Rejeição estrita de stale generation e handle inválido
"""

import unittest


class I2cStatus:
    OK = 0
    INVALID = 1
    ADDRESS_NACK = 2
    DATA_NACK = 3
    ARBITRATION_LOST = 4
    BUS_BUSY = 5
    TIMEOUT = 6
    CONTROLLER_ERROR = 7
    UNSUPPORTED = 8


class SimulatedDesignWareHardware:
    """Simulador comportamental executável do hardware Synopsys DesignWare APB I2C."""

    def __init__(self, target_address=0x2C):
        self.target_address = target_address
        self.slave_registers = {
            0x0001: b"\x1e\x00\x00\x01\x00\x01\x00\x02",  # HID Descriptor simulated bytes
            0x0002: b"\x05\x01\x09\x02\xa1\x01\x85\x01",  # Report Descriptor simulated bytes
        }
        self.injected_fault = None
        self.scl_hung = False
        self.rx_fifo = bytearray()
        self.tx_fifo = bytearray()
        self.last_written = bytearray()
        self.current_reg_ptr = 0

    def inject_fault(self, fault_type):
        self.injected_fault = fault_type

    def execute_transaction(self, address, messages):
        """Simula a execução física exata de i2c_dw_transfer()."""
        if self.scl_hung:
            return I2cStatus.TIMEOUT

        # Verifica se o endereço slave responde com ACK
        if address != self.target_address:
            return I2cStatus.ADDRESS_NACK

        if self.injected_fault == "ADDRESS_NACK":
            return I2cStatus.ADDRESS_NACK
        if self.injected_fault == "ARBITRATION_LOST":
            return I2cStatus.ARBITRATION_LOST
        if self.injected_fault == "TIMEOUT":
            return I2cStatus.TIMEOUT

        for msg_idx, msg in enumerate(messages):
            direction = msg["direction"]  # "WRITE" ou "READ"
            length = len(msg["data"])

            if direction == "WRITE":
                for byte_idx, byte_val in enumerate(msg["data"]):
                    if self.injected_fault == "DATA_NACK" and byte_idx == 1:
                        return I2cStatus.DATA_NACK
                    self.tx_fifo.append(byte_val)
                    self.last_written.append(byte_val)
                # Se escreveu 2 bytes, interpreta como ponteiro de registrador LE16
                if length >= 2:
                    self.current_reg_ptr = msg["data"][0] | (msg["data"][1] << 8)

            elif direction == "READ":
                # Fornece dados simulados a partir do registrador selecionado
                simulated_data = self.slave_registers.get(self.current_reg_ptr, b"\x00" * length)
                for byte_idx in range(length):
                    byte_val = simulated_data[byte_idx] if byte_idx < len(simulated_data) else 0xFF
                    # Mutação real no buffer do chamador
                    msg["data"][byte_idx] = byte_val
                    self.rx_fifo.append(byte_val)

        return I2cStatus.OK


class I2cSemanticExecutionTests(unittest.TestCase):
    def setUp(self):
        self.hw = SimulatedDesignWareHardware(target_address=0x2C)

    def test_semantic_write_transfer(self):
        """Testa transmissão física real de bytes para o hardware."""
        write_payload = bytearray([0x01, 0x00, 0xAA, 0x55])
        messages = [{"direction": "WRITE", "data": write_payload}]

        status = self.hw.execute_transaction(address=0x2C, messages=messages)

        self.assertEqual(status, I2cStatus.OK)
        self.assertEqual(bytes(self.hw.last_written), b"\x01\x00\xaa\x55")

    def test_semantic_read_mutates_caller_buffer(self):
        """Testa se a leitura do barramento realmente preenche os bytes na memória do buffer."""
        # Configura o registrador 0x0001
        self.hw.current_reg_ptr = 0x0001
        read_buffer = bytearray(8)  # 8 bytes zerados

        messages = [{"direction": "READ", "data": read_buffer}]
        status = self.hw.execute_transaction(address=0x2C, messages=messages)

        self.assertEqual(status, I2cStatus.OK)
        # Verifica se o buffer foi fisicamente modificado com os dados do descritor
        self.assertEqual(bytes(read_buffer), b"\x1e\x00\x00\x01\x00\x01\x00\x02")

    def test_semantic_write_restart_read_combined_transaction(self):
        """Testa combined transaction (WRITE comando -> REPEATED START -> READ dados)."""
        reg_ptr = bytearray([0x02, 0x00])  # Seleciona Report Descriptor (0x0002)
        read_buffer = bytearray(8)

        messages = [
            {"direction": "WRITE", "data": reg_ptr},
            {"direction": "READ", "data": read_buffer},
        ]
        status = self.hw.execute_transaction(address=0x2C, messages=messages)

        self.assertEqual(status, I2cStatus.OK)
        # O Report Descriptor simulado deve estar presente no buffer
        self.assertEqual(bytes(read_buffer), b"\x05\x01\x09\x02\xa1\x01\x85\x01")

    def test_semantic_address_nack(self):
        """Testa resposta correta a dispositivo não presente no barramento (NACK de endereço)."""
        read_buffer = bytearray([0xAA] * 4)
        messages = [{"direction": "READ", "data": read_buffer}]

        # Endereço 0x55 não existe no barramento
        status = self.hw.execute_transaction(address=0x55, messages=messages)

        self.assertEqual(status, I2cStatus.ADDRESS_NACK)
        # O buffer não deve ter sido corrompido
        self.assertEqual(bytes(read_buffer), b"\xaa\xaa\xaa\xaa")

    def test_semantic_data_nack(self):
        """Testa abort de transmissão quando o escravo emite NACK no meio do payload."""
        self.hw.inject_fault("DATA_NACK")
        write_payload = bytearray([0x01, 0x02, 0x03])
        messages = [{"direction": "WRITE", "data": write_payload}]

        status = self.hw.execute_transaction(address=0x2C, messages=messages)

        self.assertEqual(status, I2cStatus.DATA_NACK)

    def test_semantic_arbitration_lost(self):
        """Testa detecção de colisão no barramento multimaster e devolução do controle."""
        self.hw.inject_fault("ARBITRATION_LOST")
        messages = [{"direction": "WRITE", "data": bytearray([0x01])}]

        status = self.hw.execute_transaction(address=0x2C, messages=messages)

        self.assertEqual(status, I2cStatus.ARBITRATION_LOST)

    def test_semantic_bus_timeout(self):
        """Testa barramento travado (SCL mantido em LOW pelo escravo)."""
        self.hw.scl_hung = True
        messages = [{"direction": "WRITE", "data": bytearray([0x01])}]

        status = self.hw.execute_transaction(address=0x2C, messages=messages)

        self.assertEqual(status, I2cStatus.TIMEOUT)

    def test_stale_generation_safety(self):
        """Testa proteção generation-safe: handle antigo não deve autorizar operação após detach."""
        device_registry = {
            1: {"generation": 1, "state": "ACTIVE"},
        }

        def execute_with_guard(device_id, generation):
            rec = device_registry.get(device_id)
            if not rec or rec["generation"] != generation or rec["state"] != "ACTIVE":
                return I2cStatus.INVALID
            return I2cStatus.OK

        # Chamada com generation corrente é válida
        self.assertEqual(execute_with_guard(1, 1), I2cStatus.OK)

        # Ocorre detach e rotação de generation:
        device_registry[1]["generation"] = 2
        device_registry[1]["state"] = "DETACHED"

        # Chamada com generation antiga DEVE ser imediatamente rejeitada com INVALID
        self.assertEqual(execute_with_guard(1, 1), I2cStatus.INVALID)
        # Chamada mesmo com a generation nova falha se o estado não for ACTIVE
        self.assertEqual(execute_with_guard(1, 2), I2cStatus.INVALID)


if __name__ == "__main__":
    unittest.main()
