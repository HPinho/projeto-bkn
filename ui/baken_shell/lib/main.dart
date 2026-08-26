import 'package:flutter/material.dart';
import 'dart:ui';
import 'dart:math' as math;

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const BakenOSDesktopApp());
}

class BakenOSDesktopApp extends StatelessWidget {
  const BakenOSDesktopApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Baken OS — Aero-Quantum Desktop',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF060913),
        fontFamily: 'Segoe UI',
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00E5FF),
          secondary: Color(0xFF818CF8),
          surface: Color(0xFF0F172A),
        ),
      ),
      home: const BakenDesktopShell(),
    );
  }
}

class BakenDesktopShell extends StatefulWidget {
  const BakenDesktopShell({super.key});

  @override
  State<BakenDesktopShell> createState() => _BakenDesktopShellState();
}

class _BakenDesktopShellState extends State<BakenDesktopShell> with SingleTickerProviderStateMixin {
  bool _startMenuOpen = false;
  bool _controlCenterOpen = false;
  
  // Janelas Abertas
  bool _ideOpen = true;
  bool _qpuOpen = true;
  bool _termOpen = true;
  bool _fsOpen = false;
  bool _audioOpen = false;

  // Estado do Q-HAL (Simulador Quântico)
  double _theta = math.pi / 4;
  double _phi = math.pi / 3;
  double _fidelity = 99.98;
  String _activeStateName = '(|00⟩ + |11⟩) / √2 (Bell State)';

  // Estado do Terminal
  final List<Map<String, String>> _termLines = [
    {'type': 'sys', 'text': 'Baken OS v1.0.0-PROD (Aero-Quantum Kernel)'},
    {'type': 'sys', 'text': 'Criptografia PQC: ML-KEM-768 + ML-DSA-65 Ativa [OK]'},
    {'type': 'sys', 'text': 'Digite "qpu bell", "bknc build", "fs ls", "audio play" ou "help"'},
  ];
  final TextEditingController _termCtrl = TextEditingController();
  final FocusNode _termFocus = FocusNode();

  late AnimationController _animCtrl;

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 12),
    )..repeat();
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    _termCtrl.dispose();
    _termFocus.dispose();
    super.dispose();
  }

  void _handleCommand(String cmd) {
    cmd = cmd.trim();
    if (cmd.isEmpty) return;

    setState(() {
      _termLines.add({'type': 'input', 'text': 'baken-kernel# $cmd'});

      final lower = cmd.toLowerCase();
      if (lower == 'help') {
        _termLines.add({'type': 'out', 'text': 'Comandos: qpu bell, qpu hadamard, bknc build, bknc run, fs ls, audio play, clear, menu'});
      } else if (lower.startsWith('qpu bell')) {
        _theta = math.pi / 2;
        _phi = 0;
        _fidelity = 99.99;
        _activeStateName = '(|00⟩ + |11⟩) / √2 [Bell State EPR]';
        _termLines.add({'type': 'success', 'text': '[Q-HAL] Par Bell Entrelaçado gerado com Sucesso! Fidelidade: 99.99%'});
      } else if (lower.startsWith('qpu hadamard')) {
        _theta = math.pi / 2;
        _phi = math.pi / 2;
        _activeStateName = '(|0⟩ + |1⟩) / √2 [|+⟩ Superposição]';
        _termLines.add({'type': 'success', 'text': '[Q-HAL] Porta de Hadamard aplicada no Qubit #0'});
      } else if (lower.startsWith('bknc build')) {
        _termLines.add({'type': 'success', 'text': '[BKNC] Compilando quantum_teleport.bkn para binário assinado com ML-DSA...'});
        _termLines.add({'type': 'success', 'text': '[BKNC] Gerado: build/quantum_teleport.bkn_exec (Tamanho: 4.2 KB) [OK]'});
      } else if (lower.startsWith('bknc run')) {
        _termLines.add({'type': 'out', 'text': '[BKN Runtime] Executando quantum_teleport.bkn_exec no Ring 0...'});
        _termLines.add({'type': 'success', 'text': '[Telemetria] Teletransporte Quântico Concluído: m0=0, m1=1'});
      } else if (lower.startsWith('fs ls')) {
        _termLines.add({'type': 'out', 'text': 'BakenFS (Partição NVMe Criptografada):'});
        _termLines.add({'type': 'out', 'text': '  - /kernel/main.bkn (12.4 KB)'});
        _termLines.add({'type': 'out', 'text': '  - /kernel/quantum.bkn (8.1 KB)'});
        _termLines.add({'type': 'out', 'text': '  - /bin/bknc.bkn_exec (48.0 KB)'});
        _termLines.add({'type': 'out', 'text': '  - /system/libbkn.a (128.0 KB)'});
      } else if (lower.startsWith('audio play') || lower.startsWith('sound')) {
        _audioOpen = true;
        _termLines.add({'type': 'success', 'text': '[Intel HDA] Reproduzindo Jingle Harmônico Quântico (48 kHz Stereo DMA)'});
      } else if (lower == 'clear') {
        _termLines.clear();
      } else if (lower == 'menu') {
        _startMenuOpen = !_startMenuOpen;
      } else {
        _termLines.add({'type': 'err', 'text': 'Comando não reconhecido. Digite "help" para lista.'});
      }
    });

    _termCtrl.clear();
    _termFocus.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // 1. Papel de Parede Aero-Quantum com Mesh Gradient Vivo
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _animCtrl,
              builder: (context, child) {
                final val = _animCtrl.value * 2 * math.pi;
                return Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment(math.sin(val) * 0.4 - 0.6, -0.8),
                      end: Alignment(math.cos(val) * 0.4 + 0.6, 0.9),
                      colors: const [
                        Color(0xFF0F172A),
                        Color(0xFF0B1021),
                        Color(0xFF1E1B4B),
                        Color(0xFF030712),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),

          // 2. Área de Trabalho com Janelas Reais
          Positioned.fill(
            child: Column(
              children: [
                _buildTopBar(),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 80),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Coluna Esquerda: IDE + Terminal
                        Expanded(
                          flex: 5,
                          child: Column(
                            children: [
                              if (_ideOpen)
                                Expanded(
                                  flex: 6,
                                  child: _buildBknStudioIde(),
                                ),
                              if (_ideOpen && _termOpen) const SizedBox(height: 12),
                              if (_termOpen)
                                Expanded(
                                  flex: 4,
                                  child: _buildInteractiveTerminal(),
                                ),
                            ],
                          ),
                        ),

                        const SizedBox(width: 12),

                        // Coluna Direita: Q-HAL Monitor 3D + File Explorer
                        Expanded(
                          flex: 4,
                          child: Column(
                            children: [
                              if (_qpuOpen)
                                Expanded(
                                  flex: 6,
                                  child: _buildQHal3DMonitor(),
                                ),
                              if (_qpuOpen && _fsOpen) const SizedBox(height: 12),
                              if (_fsOpen)
                                Expanded(
                                  flex: 4,
                                  child: _buildBakenFsExplorer(),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // 3. Menu Iniciar Glassmorphic (Popup)
          if (_startMenuOpen)
            Positioned(
              top: 44,
              left: 12,
              child: _buildStartMenu(),
            ),

          // 4. Central de Controle Lateral (Popup)
          if (_controlCenterOpen)
            Positioned(
              top: 44,
              right: 12,
              child: _buildControlCenter(),
            ),

          // 5. Dock Flutuante Inferior com Efeito Halo Glow
          Positioned(
            bottom: 12,
            left: 0,
            right: 0,
            child: Center(
              child: _buildFloatingDock(),
            ),
          ),
        ],
      ),
    );
  }

  // --- Top Status Bar ---
  Widget _buildTopBar() {
    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          height: 38,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: const Color(0x0AFFFFFF),
            border: Border(bottom: BorderSide(color: const Color(0x14FFFFFF))),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                // Botão do Menu Iniciar [B]
                InkWell(
                  onTap: () => setState(() => _startMenuOpen = !_startMenuOpen),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: _startMenuOpen ? const Color(0x3300E5FF) : const Color(0x0FFFFFFF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0x6600E5FF)),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.blur_on, color: Color(0xFF00E5FF), size: 15),
                        SizedBox(width: 5),
                        Text('BAKEN OS', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11, letterSpacing: 1.2, color: Color(0xFF00E5FF))),
                      ],
                    ),
                  ),
                ),

                const SizedBox(width: 14),
                _topBarMenuBtn('Arquivo'),
                _topBarMenuBtn('Editar'),
                _topBarMenuBtn('Compilar (bknc)'),
                _topBarMenuBtn('Q-HAL Co-Proc'),
                _topBarMenuBtn('BakenFS'),

                const SizedBox(width: 20),

                // Status Chips
                _topBarChip(Icons.shield_outlined, 'ML-DSA PQC', const Color(0xFF10B981)),
                const SizedBox(width: 10),
                _topBarChip(Icons.wifi, 'Wi-Fi 7 (5.8 Gbps)', const Color(0xFF38BDF8)),
                const SizedBox(width: 10),
                _topBarChip(Icons.volume_up, 'Intel HDA 48k', const Color(0xFFA855F7)),

                const SizedBox(width: 14),

                // Botão da Central de Controle / Relógio
                InkWell(
                  onTap: () => setState(() => _controlCenterOpen = !_controlCenterOpen),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                    child: const Row(
                      children: [
                        Icon(Icons.tune, size: 13, color: Colors.white70),
                        SizedBox(width: 5),
                        Text('10:00 AM', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _topBarMenuBtn(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6),
      child: Text(title, style: const TextStyle(fontSize: 11, color: Colors.white70)),
    );
  }

  Widget _topBarChip(IconData icon, String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w600)),
      ],
    );
  }

  // --- Janela: BKN Studio IDE ---
  Widget _buildBknStudioIde() {
    return _buildGlassCard(
      title: 'BKN Studio IDE — quantum_teleport.bkn',
      icon: Icons.code,
      onClose: () => setState(() => _ideOpen = false),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Abas
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            color: const Color(0x33000000),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildTab('quantum_teleport.bkn', true),
                  const SizedBox(width: 6),
                  _buildTab('main.bkn', false),
                  const SizedBox(width: 6),
                  _buildTab('crypto.bkn', false),
                ],
              ),
            ),
          ),
          // Editor de Código
          const Expanded(
            child: Padding(
              padding: EdgeInsets.all(12),
              child: SingleChildScrollView(
                child: SelectableText(
                  '// Baken Language v1.0 — Módulo de Teletransporte Quântico Soberano\n'
                  'module kernel::quantum_teleport;\n\n'
                  'import libbkn::quantum::*;\n'
                  'import libbkn::crypto::*;\n\n'
                  '@quantum\n'
                  'pub fn teleport_state(src: qubit, mut bell: qreg[2]) -> (u8, u8) {\n'
                  '    quantum {\n'
                  '        H(bell[0]);\n'
                  '        CNOT(bell[0], bell[1]); // Canal Entrelacado (|00> + |11>)/sqrt(2)\n'
                  '        CNOT(src, bell[0]);\n'
                  '        H(src);\n'
                  '    }\n\n'
                  '    let m0 = measure(src);\n'
                  '    let m1 = measure(bell[0]);\n'
                  '    return (m0, m1); // Zero-Copy Telemetry enviada ao Q-HAL\n'
                  '}\n',
                  style: TextStyle(
                    fontFamily: 'Consolas',
                    fontSize: 12,
                    height: 1.45,
                    color: Color(0xFF38BDF8),
                  ),
                ),
              ),
            ),
          ),
          // Rodapé da IDE
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
            decoration: BoxDecoration(
              color: const Color(0x991E1B4B),
              border: Border(top: BorderSide(color: const Color(0x0FFFFFFF))),
            ),
            child: const Row(
              children: [
                Expanded(
                  child: Text(
                    'BKN Language v1.0 | 0 Erros | AVX-512 Ready',
                    style: TextStyle(fontSize: 10, color: Color(0xFF00E5FF)),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Text('UTF-8 | Ln 15, Col 2', style: TextStyle(fontSize: 10, color: Colors.white54)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTab(String title, bool active) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: active ? const Color(0xFF312E81) : const Color(0x0AFFFFFF),
        borderRadius: BorderRadius.circular(5),
        border: Border.all(color: active ? const Color(0xFF00E5FF) : const Color(0x0FFFFFFF)),
      ),
      child: Text(title, style: TextStyle(fontSize: 10, color: active ? const Color(0xFF00E5FF) : Colors.white70)),
    );
  }

  // --- Janela: Terminal Interativo Baken Shell ---
  Widget _buildInteractiveTerminal() {
    return _buildGlassCard(
      title: 'Baken Shell — Console Interativo em BKN Puro',
      icon: Icons.terminal,
      onClose: () => setState(() => _termOpen = false),
      child: Container(
        color: const Color(0xE6090D1A),
        padding: const EdgeInsets.all(10),
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                itemCount: _termLines.length,
                itemBuilder: (context, index) {
                  final line = _termLines[index];
                  Color col = Colors.white70;
                  if (line['type'] == 'sys') col = const Color(0xFF38BDF8);
                  if (line['type'] == 'input') col = const Color(0xFF10B981);
                  if (line['type'] == 'success') col = const Color(0xFF00E5FF);
                  if (line['type'] == 'err') col = Colors.redAccent;

                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 1.5),
                    child: Text(
                      line['text']!,
                      style: TextStyle(fontFamily: 'Consolas', fontSize: 11, color: col),
                    ),
                  );
                },
              ),
            ),
            const Divider(color: Colors.white12, height: 6),
            Row(
              children: [
                const Text('baken# ', style: TextStyle(fontFamily: 'Consolas', fontSize: 12, color: Color(0xFF10B981), fontWeight: FontWeight.bold)),
                Expanded(
                  child: TextField(
                    controller: _termCtrl,
                    focusNode: _termFocus,
                    onSubmitted: _handleCommand,
                    style: const TextStyle(fontFamily: 'Consolas', fontSize: 12, color: Colors.white),
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      isDense: true,
                      contentPadding: EdgeInsets.zero,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // --- Janela: Q-HAL Monitor 3D (Bloch Sphere) ---
  Widget _buildQHal3DMonitor() {
    return _buildGlassCard(
      title: 'Q-HAL 3D State Co-Processor',
      icon: Icons.blur_on,
      onClose: () => setState(() => _qpuOpen = false),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          children: [
            Expanded(
              child: CustomPaint(
                painter: BlochSphere3DPainter(theta: _theta, phi: _phi),
                child: Container(),
              ),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0x4D000000),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0x3300E5FF)),
              ),
              child: Column(
                children: [
                  _telemetryRow('Estado:', _activeStateName, const Color(0xFF00E5FF)),
                  const SizedBox(height: 3),
                  _telemetryRow('Fidelidade:', '$_fidelity%', const Color(0xFF10B981)),
                  const SizedBox(height: 3),
                  _telemetryRow('Blindagem:', 'ML-KEM Kyber', const Color(0xFFA855F7)),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _handleCommand('qpu bell'),
                    icon: const Icon(Icons.hub, size: 12),
                    label: const Text('Par Bell', style: TextStyle(fontSize: 10)),
                    style: ElevatedButton.styleFrom(
                      padding: EdgeInsets.zero,
                      backgroundColor: const Color(0x3300E5FF),
                      foregroundColor: const Color(0xFF00E5FF),
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _handleCommand('qpu hadamard'),
                    icon: const Icon(Icons.transform, size: 12),
                    label: const Text('Hadamard', style: TextStyle(fontSize: 10)),
                    style: ElevatedButton.styleFrom(
                      padding: EdgeInsets.zero,
                      backgroundColor: const Color(0x3310B981),
                      foregroundColor: const Color(0xFF10B981),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _telemetryRow(String k, String v, Color col) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(k, style: const TextStyle(fontSize: 10, color: Colors.white54)),
        Flexible(
          child: Text(
            v,
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: col),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  // --- Janela: BakenFS Explorer ---
  Widget _buildBakenFsExplorer() {
    return _buildGlassCard(
      title: 'BakenFS Explorer — NVMe',
      icon: Icons.folder,
      onClose: () => setState(() => _fsOpen = false),
      child: ListView(
        padding: const EdgeInsets.all(6),
        children: [
          _fileTile('quantum_teleport.bkn', '12.4 KB', 'Código Fonte BKN'),
          _fileTile('main.bkn', '18.2 KB', 'Microkernel Core'),
          _fileTile('bknc.bkn_exec', '48.0 KB', 'Binário Compilado'),
          _fileTile('libbkn.a', '128.0 KB', 'Biblioteca Estática'),
        ],
      ),
    );
  }

  Widget _fileTile(String name, String size, String desc) {
    return ListTile(
      dense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
      leading: const Icon(Icons.description, color: Color(0xFF38BDF8), size: 18),
      title: Text(name, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
      subtitle: Text(desc, style: const TextStyle(fontSize: 9, color: Colors.white54)),
      trailing: Text(size, style: const TextStyle(fontSize: 10, color: Color(0xFF00E5FF))),
    );
  }

  // --- Menu Iniciar ---
  Widget _buildStartMenu() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
        child: Container(
          width: 300,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xEB0D1224),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0x4D00E5FF)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x99000000),
                blurRadius: 30,
                spreadRadius: 8,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Barra de Busca
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0x0FFFFFFF),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0x1AFFFFFF)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.search, size: 14, color: Colors.white54),
                    SizedBox(width: 6),
                    Text('Buscar apps, BKN e comandos...', style: TextStyle(fontSize: 11, color: Colors.white54)),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const Text('APLICATIVOS SOBERANOS', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF00E5FF), letterSpacing: 1.2)),
              const SizedBox(height: 8),
              _appMenuItem(Icons.code, 'BKN Studio IDE', 'Ambiente de Desenvolvimento', () {
                setState(() { _ideOpen = true; _startMenuOpen = false; });
              }),
              _appMenuItem(Icons.blur_on, 'Q-HAL Quantum Monitor', 'Simulador 3D Linear', () {
                setState(() { _qpuOpen = true; _startMenuOpen = false; });
              }),
              _appMenuItem(Icons.terminal, 'Terminal Baken Shell', 'Console do Microkernel', () {
                setState(() { _termOpen = true; _startMenuOpen = false; });
              }),
              _appMenuItem(Icons.folder, 'BakenFS Explorer', 'Gerenciador de Arquivos', () {
                setState(() { _fsOpen = true; _startMenuOpen = false; });
              }),
              const Divider(color: Colors.white12, height: 16),
              // Cartão de Saúde do Kernel
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0x1A10B981),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0x4D10B981)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.verified, color: Color(0xFF10B981), size: 16),
                    SizedBox(width: 6),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Microkernel Soberano', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF10B981))),
                        Text('Memória: 512 MB / 4096 MB', style: TextStyle(fontSize: 9, color: Colors.white54)),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _appMenuItem(IconData icon, String title, String subtitle, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5, horizontal: 6),
        child: Row(
          children: [
            Icon(icon, color: const Color(0xFF00E5FF), size: 18),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                Text(subtitle, style: const TextStyle(fontSize: 9, color: Colors.white54)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // --- Central de Controle Lateral ---
  Widget _buildControlCenter() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
        child: Container(
          width: 260,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xEB0D1224),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0x4D818CF8)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('CENTRAL DE CONTROLE', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF818CF8), letterSpacing: 1.2)),
              const SizedBox(height: 10),
              _controlTile(Icons.wifi, 'Wi-Fi 7 MLO', 'Conectado (5.8 Gbps)', true),
              _controlTile(Icons.bluetooth, 'Bluetooth 5.4', 'Logitech G903 OK', true),
              _controlTile(Icons.volume_up, 'Intel HD Audio', '48 kHz Stereo', true),
              _controlTile(Icons.shield, 'Blindagem ML-DSA', 'Ativo 100%', true),
            ],
          ),
        ),
      ),
    );
  }

  Widget _controlTile(IconData icon, String title, String val, bool active) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: const Color(0x0AFFFFFF),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: const Color(0x14FFFFFF)),
        ),
        child: Row(
          children: [
            Icon(icon, size: 16, color: active ? const Color(0xFF00E5FF) : Colors.white38),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600)),
                Text(val, style: const TextStyle(fontSize: 9, color: Colors.white54)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // --- Dock Inferior Flutuante ---
  Widget _buildFloatingDock() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0xBF0F172A),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0x26FFFFFF)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x2600E5FF),
                blurRadius: 16,
                spreadRadius: 2,
              ),
            ],
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _dockItem(Icons.blur_on, 'Menu Iniciar', () => setState(() => _startMenuOpen = !_startMenuOpen), _startMenuOpen),
                _dockDivider(),
                _dockItem(Icons.terminal, 'Terminal', () => setState(() => _termOpen = !_termOpen), _termOpen),
                _dockItem(Icons.code, 'BKN Studio', () => setState(() => _ideOpen = !_ideOpen), _ideOpen),
                _dockItem(Icons.hub, 'Q-HAL Monitor', () => setState(() => _qpuOpen = !_qpuOpen), _qpuOpen),
                _dockItem(Icons.folder, 'BakenFS', () => setState(() => _fsOpen = !_fsOpen), _fsOpen),
                _dockItem(Icons.volume_up, 'Intel HDA Audio', () => setState(() => _audioOpen = !_audioOpen), _audioOpen),
                _dockItem(Icons.settings, 'Configurações', () => setState(() => _controlCenterOpen = !_controlCenterOpen), _controlCenterOpen),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _dockItem(IconData icon, String tooltip, VoidCallback onTap, bool isOpen) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          width: 40,
          height: 40,
          margin: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(
            color: isOpen ? const Color(0x2600E5FF) : const Color(0x0DFFFFFF),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: isOpen ? const Color(0x6600E5FF) : const Color(0x14FFFFFF)),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: isOpen ? const Color(0xFF00E5FF) : Colors.white, size: 20),
              if (isOpen)
                Container(
                  width: 3.5,
                  height: 3.5,
                  margin: const EdgeInsets.only(top: 2),
                  decoration: const BoxDecoration(
                    color: Color(0xFF00E5FF),
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _dockDivider() {
    return Container(
      width: 1,
      height: 20,
      margin: const EdgeInsets.symmetric(horizontal: 6),
      color: Colors.white12,
    );
  }

  // --- Container Genérico de Janela Glassmorphic ---
  Widget _buildGlassCard({
    required String title,
    required IconData icon,
    required VoidCallback onClose,
    required Widget child,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
        child: Container(
          decoration: BoxDecoration(
            color: const Color(0xD90B1020),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0x1FFFFFFF)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x66000000),
                blurRadius: 16,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0x0AFFFFFF),
                  border: Border(bottom: BorderSide(color: const Color(0x0FFFFFFF))),
                ),
                child: Row(
                  children: [
                    _winCircle(Colors.redAccent, onClose),
                    const SizedBox(width: 5),
                    _winCircle(Colors.amberAccent, null),
                    const SizedBox(width: 5),
                    _winCircle(Colors.greenAccent, null),
                    const SizedBox(width: 10),
                    Icon(icon, size: 13, color: const Color(0xFF00E5FF)),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.white),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(child: child),
            ],
          ),
        ),
      ),
    );
  }

  Widget _winCircle(Color color, VoidCallback? onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(5),
      child: Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
      ),
    );
  }
}

// --- Pintor Vetorial da Esfera de Bloch 3D em Tempo Real ---
class BlochSphere3DPainter extends CustomPainter {
  final double theta;
  final double phi;

  BlochSphere3DPainter({required this.theta, required this.phi});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) * 0.38;

    // Fundo da Esfera
    final spherePaint = Paint()
      ..shader = RadialGradient(
        colors: const [
          Color(0xE60E1528),
          Color(0xF205070E),
        ],
      ).createShader(Rect.fromCircle(center: center, radius: radius));
    canvas.drawCircle(center, radius, spherePaint);

    final borderPaint = Paint()
      ..color = const Color(0x9938BDF8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    canvas.drawCircle(center, radius, borderPaint);

    // Equador
    final equatorPaint = Paint()
      ..color = const Color(0x6606B6D4)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
    canvas.drawOval(
      Rect.fromCenter(center: center, width: radius * 2, height: radius * 0.6),
      equatorPaint,
    );

    // Eixos Z e X
    final axisPaint = Paint()
      ..color = const Color(0xB338BDF8)
      ..strokeWidth = 1.2;
    canvas.drawLine(Offset(center.dx, center.dy - radius - 8), Offset(center.dx, center.dy + radius + 8), axisPaint);
    canvas.drawLine(Offset(center.dx - radius - 8, center.dy), Offset(center.dx + radius + 8, center.dy), axisPaint);

    // Vetor de Estado Quântico |Psi>
    final vx = radius * math.sin(theta) * math.cos(phi);
    final vy = -radius * math.cos(theta); // Invertido para o topo ser |0>
    final target = Offset(center.dx + vx, center.dy + vy);

    final vectorPaint = Paint()
      ..color = const Color(0xFF00E5FF)
      ..strokeWidth = 2.2;
    canvas.drawLine(center, target, vectorPaint);

    // Ponto de Colapso do Vetor
    canvas.drawCircle(target, 5, Paint()..color = const Color(0xFF00E5FF));
    canvas.drawCircle(target, 2.5, Paint()..color = Colors.white);

    // Rótulos dos Polos |0> e |1>
    _drawText(canvas, '|0⟩', Offset(center.dx - 6, center.dy - radius - 18), const Color(0xFF38BDF8));
    _drawText(canvas, '|1⟩', Offset(center.dx - 6, center.dy + radius + 6), const Color(0xFF38BDF8));
    _drawText(canvas, '|+⟩', Offset(center.dx + radius + 8, center.dy - 6), const Color(0xFF10B981));
    _drawText(canvas, '|–⟩', Offset(center.dx - radius - 20, center.dy - 6), const Color(0xFF10B981));
  }

  void _drawText(Canvas canvas, String text, Offset pos, Color color) {
    final tp = TextPainter(
      text: TextSpan(text: text, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, pos);
  }

  @override
  bool shouldRepaint(covariant BlochSphere3DPainter oldDelegate) => true;
}
