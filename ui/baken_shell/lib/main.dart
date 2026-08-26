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
      title: 'Baken OS — Sovereign Desktop (Phases 1-20 Complete)',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.light,
        fontFamily: 'Segoe UI',
        scaffoldBackgroundColor: const Color(0xFFF3E8FF),
        colorScheme: const ColorScheme.light(
          primary: Color(0xFF00E5FF),
          secondary: Color(0xFF8B5CF6),
          surface: Color(0xFFFFFFFF),
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

class _BakenDesktopShellState extends State<BakenDesktopShell> with TickerProviderStateMixin {
  // Estados de Interface
  bool _startMenuOpen = false;
  bool _settingsOpen = true;
  bool _terminalOpen = true;
  bool _qpuOpen = false;
  bool _aiCopilotOpen = true;
  bool _bakenFsOpen = false;
  bool _calendarWidgetOpen = true;
  bool _weatherWidgetOpen = true;
  bool _voiceListening = false;

  // Maximização de Janelas
  bool _settingsMaximized = false;
  bool _terminalMaximized = false;
  bool _aiMaximized = false;

  // Aba Ativa no Copiloto Q-HAL IA (0: Living Chat, 1: Kernel IPC, 2: QN-Bus & DynaJIT, 3: Vector BakenFS, 4: Capabilities & Bridge, 5: Mesh & QPU)
  int _activeAiTab = 0;

  // Estado Quântico Q-HAL
  double _theta = math.pi / 4;
  double _phi = math.pi / 3;
  double _fidelity = 99.99;
  String _activeStateName = '(|00⟩ + |11⟩) / √2 (Bell State)';

  // Telemetria Viva do Kernel Ring 0 (Fases 1 a 20)
  int _activeQubits = 32;
  double _avxThroughputGFlops = 142.8;
  double _kernelMemoryDefragRate = 99.8;
  int _qnBusLatencyNs = 42;
  double _dynaJitSpeedup = 1.64;
  int _instantBootMs = 640;
  String _pqcStatus = 'ML-KEM-768 [Enclave Ring 0 Secured]';

  // Busca Semântica Vetorial (Fase 14)
  String _searchQuery = '';
  final List<Map<String, dynamic>> _semanticResults = [
    {'name': 'crypto_pqc_shield.bkn', 'score': 0.985, 'cat': 'PQC Encryption Enclave', 'time': '10 mins ago'},
    {'name': 'quantum_teleport.bkn', 'score': 0.942, 'cat': 'Q-HAL Bell Algorithm', 'time': '1 file ago'},
    {'name': 'self_healing.bkn', 'score': 0.891, 'cat': 'Zero-Crash Microkernel', 'time': 'Fase 6 Active'},
    {'name': 'qn_bus.bkn', 'score': 0.860, 'cat': 'Lockless L3 Bus (< 50ns)', 'time': 'Fase 13 Active'},
  ];

  // Estado do Terminal
  final List<Map<String, String>> _termLines = [
    {'type': 'sys', 'text': '[Baken OS v2.0] Microkernel Soberano Ring 0 (Todas as 20 Fases Ativas).'},
    {'type': 'sys', 'text': '[QN-Bus] Latência L3: 42 ns | DynaJIT: +64% Speedup | InstantBoot: 640 ms.'},
    {'type': 'sys', 'text': '[Vector BakenFS] Inodes com Embeddings de 384 Dimensões [Pronto].'},
    {'type': 'sys', 'text': '[Zero-Trust Vault] Tokens ML-DSA-65 Ativos | BakenBridge POSIX [OK].'},
    {'type': 'info', 'text': 'Digite "ai <pergunta>", "bkn pkg install <app>", "qpu bell" ou "help".'},
  ];
  final TextEditingController _termCtrl = TextEditingController();
  final FocusNode _termFocus = FocusNode();

  // Estado do Copiloto Q-HAL IA
  final List<Map<String, String>> _aiChatHistory = [
    {
      'role': 'ai',
      'text': 'Olá! Sou o **Q-HAL AI Core v2.0**. Todas as **20 fases da arquitetura soberana** estão integradas e operantes: QN-Bus (< 42ns), BakenFS Vetorial, DynaJIT (+64%), Capabilities Zero-Trust e Boot Instantâneo (640ms).'
    }
  ];
  final TextEditingController _aiInputCtrl = TextEditingController();
  final ScrollController _aiScrollCtrl = ScrollController();
  bool _aiIsThinking = false;

  // Animações
  late AnimationController _meshAnimCtrl;
  late AnimationController _vortexAnimCtrl;
  late AnimationController _orbAnimCtrl;

  @override
  void initState() {
    super.initState();
    _meshAnimCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 16),
    )..repeat(reverse: true);

    _vortexAnimCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 20),
    )..repeat();

    _orbAnimCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();
  }

  @override
  void dispose() {
    _meshAnimCtrl.dispose();
    _vortexAnimCtrl.dispose();
    _orbAnimCtrl.dispose();
    _termCtrl.dispose();
    _termFocus.dispose();
    _aiInputCtrl.dispose();
    _aiScrollCtrl.dispose();
    super.dispose();
  }

  void _handleCommand(String cmd) {
    cmd = cmd.trim();
    if (cmd.isEmpty) return;

    setState(() {
      _termLines.add({'type': 'input', 'text': 'baken@ring0:~\$ $cmd'});
      final lower = cmd.toLowerCase();

      if (lower.startsWith('ai ')) {
        final query = cmd.substring(3);
        _handleAiQuery(query);
      } else if (lower.startsWith('bkn pkg install ')) {
        final pkg = cmd.substring(16);
        _termLines.add({'type': 'success', 'text': '[BakenPKG] Baixando "$pkg" via rede mesh P2P (340 MB/s)...'});
        _termLines.add({'type': 'success', 'text': '[BakenPKG] Assinatura ML-DSA-65 verificada. Instalado em /bin/$pkg [OK]'});
      } else if (lower == 'help') {
        _termLines.add({'type': 'out', 'text': 'Comandos: ai <query>, bkn pkg install <pkg>, qpu bell, bknc build, fs ls, clear'});
      } else if (lower.startsWith('qpu bell')) {
        _theta = math.pi / 2;
        _phi = 0;
        _fidelity = 99.99;
        _activeStateName = '(|00⟩ + |11⟩) / √2 [Bell State EPR]';
        _termLines.add({'type': 'success', 'text': '[Q-HAL] Par Bell Entrelaçado gerado! Fidelidade: 99.99%'});
        _qpuOpen = true;
      } else if (lower.startsWith('bknc build')) {
        _avxThroughputGFlops = 195.4;
        _termLines.add({'type': 'success', 'text': '[BKNC + DynaJIT] Superotimizando com grafo neural AVX-512 (+64% boost)...'});
        _termLines.add({'type': 'success', 'text': '[BKNC] Gerado: build/quantum_teleport.bkn_exec (Assinado ML-DSA) [OK]'});
      } else if (lower.startsWith('fs ls')) {
        _termLines.add({'type': 'out', 'text': 'BakenFS v3 (Indexação Semântica Vetorial 384-D):'});
        _termLines.add({'type': 'out', 'text': '  - /kernel/main.bkn (Inode Embedding #101)'});
        _termLines.add({'type': 'out', 'text': '  - /kernel/qn_bus.bkn (Inode Embedding #102)'});
        _termLines.add({'type': 'out', 'text': '  - /kernel/dynajit.bkn (Inode Embedding #103)'});
        _termLines.add({'type': 'out', 'text': '  - /kernel/capabilities_vault.bkn (Inode Embedding #104)'});
      } else if (lower == 'settings') {
        _settingsOpen = true;
      } else if (lower == 'clear') {
        _termLines.clear();
      } else {
        _termLines.add({'type': 'err', 'text': 'Comando não reconhecido. Digite "help" ou use "ai <pergunta>".'});
      }
    });

    _termCtrl.clear();
    _termFocus.requestFocus();
  }

  void _handleAiQuery(String query) {
    if (query.trim().isEmpty) return;

    setState(() {
      _aiChatHistory.add({'role': 'user', 'text': query});
      _aiIsThinking = true;
      _aiCopilotOpen = true;
    });

    _aiInputCtrl.clear();

    Future.delayed(const Duration(milliseconds: 600), () {
      if (!mounted) return;

      String aiResponse = '';
      final lower = query.toLowerCase();

      if (lower.contains('teletransporte') || lower.contains('teleport') || lower.contains('bkn')) {
        aiResponse = 'Aqui está a implementação do algoritmo de teletransporte quântico em linguagem BKN pura:\n\n'
            '```rust\n'
            'module kernel::teleport;\n'
            'import libbkn::quantum::*;\n\n'
            '@quantum\n'
            'pub fn teleport_qubit(src: qubit) -> (u8, u8) {\n'
            '    let mut bell = qreg::alloc(2);\n'
            '    H(bell[0]);\n'
            '    CNOT(bell[0], bell[1]);\n'
            '    CNOT(src, bell[0]);\n'
            '    return (measure(src), measure(bell[0]));\n'
            '}\n'
            '```\n'
            '✅ Superotimizador AVX-512 ativado. Circuito OpenQASM 3.0 exportado com fidelidade de **99.99%**.';
      } else if (lower.contains('pqc') || lower.contains('segurança') || lower.contains('chave') || lower.contains('enclave')) {
        aiResponse = '🔒 **Auditoria PQC Soberana & Capabilities (Fases 10 & 16):**\n'
            '- Algoritmo de Encapsulamento: **ML-KEM-768** (FIPS 203)\n'
            '- Assinatura Digital de Enclave: **ML-DSA-65** (FIPS 204)\n'
            '- QN-Bus Memory Isolation: **Ativo (< 42ns de latência)**\n'
            '- Zero-Trust Capabilities: **18 enclaves ativos, 0 violações**.';
      } else if (lower.contains('otimizar') || lower.contains('circuito') || lower.contains('bell')) {
        _theta = math.pi / 2;
        _phi = 0;
        _fidelity = 99.99;
        _activeStateName = '(|00⟩ + |11⟩) / √2 [Bell State Otimizado via IA]';
        aiResponse = '⚡ **Otimização Quântica Aplicada pelo Kernel:**\n'
            '- Circuito reescalado para 2 portas EPR mínimas.\n'
            '- Fidelidade do estado Bell elevada para **99.99%**.\n'
            '- Visualização atualizada na Esfera de Bloch 3D.';
        _qpuOpen = true;
      } else if (lower.contains('boot') || lower.contains('inicialização') || lower.contains('instant')) {
        aiResponse = '🚀 **InstantBoot Telemetria (Fase 20):**\n'
            '- Tempo Total de Restauração de Imagem: **640 ms (< 800 ms)**\n'
            '- Taxa de Transferência NVMe DMA: **7200 MB/s**\n'
            '- Descriptografia de Snapshot TPM 2.0 / PQC: **Concluída com Sucesso**.';
      } else {
        aiResponse = '🤖 **Q-HAL AI Kernel Bridge:** Analisei sua instrução "$query". O microkernel transmitiu os tensores pelo QN-Bus (< 42ns), compilou via DynaJIT e executou no Ring 0 com aceleração AVX-512.';
      }

      setState(() {
        _aiChatHistory.add({'role': 'ai', 'text': aiResponse});
        _aiIsThinking = false;
        _termLines.add({'type': 'success', 'text': '[Q-HAL AI] Resposta do Kernel processada com sucesso.'});
      });

      Future.delayed(const Duration(milliseconds: 100), () {
        if (_aiScrollCtrl.hasClients) {
          _aiScrollCtrl.animateTo(
            _aiScrollCtrl.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    });
  }

  void _toggleVoiceAssistant() {
    setState(() {
      _voiceListening = !_voiceListening;
    });

    if (_voiceListening) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🎙️ Q-HAL Voice Assistant ouvindo... Diga um comando.'),
          duration: Duration(seconds: 2),
          backgroundColor: Color(0xFF0284C7),
        ),
      );
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted && _voiceListening) {
          setState(() => _voiceListening = false);
          _handleAiQuery('otimizar circuito quântico bell e auditar chaves PQC');
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    final taskbarWidth = math.min(screenSize.width - 48, 960.0);
    final taskbarLeft = (screenSize.width - taskbarWidth) / 2;

    return Scaffold(
      body: GestureDetector(
        onTap: () {
          if (_startMenuOpen) {
            setState(() => _startMenuOpen = false);
          }
        },
        behavior: HitTestBehavior.translucent,
        child: Stack(
          children: [
            // 1. Papel de Parede Mesh Gradient Suave
            Positioned.fill(
              child: AnimatedBuilder(
                animation: _meshAnimCtrl,
                builder: (context, child) {
                  final t = _meshAnimCtrl.value;
                  return Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment(-1.0 + t * 0.4, -1.0),
                        end: Alignment(1.0 - t * 0.3, 1.0),
                        colors: const [
                          Color(0xFF00E5FF),
                          Color(0xFFE879F9),
                          Color(0xFFC084FC),
                          Color(0xFFFDE047),
                          Color(0xFF4ADE80),
                        ],
                        stops: const [0.0, 0.35, 0.65, 0.88, 1.0],
                      ),
                    ),
                  );
                },
              ),
            ),

            // 2. Pastas do Desktop
            _buildDesktopFolder(x: 50, y: 60, label: 'BakenFS', iconGradient: const [Color(0xFFE879F9), Color(0xFF60A5FA)]),
            _buildDesktopFolder(x: 50, y: 150, label: 'Folders', iconGradient: const [Color(0xFF38BDF8), Color(0xFF00E5FF)]),
            _buildDesktopFolder(x: 50, y: 240, label: 'System Core', iconGradient: const [Color(0xFF818CF8), Color(0xFFC084FC)], hasVortex: true),

            // 3. Widgets do Topo Direito (Calendário e Telemetria)
            if (_calendarWidgetOpen)
              Positioned(
                top: 48,
                right: 155,
                child: _buildCalendarWidget(),
              ),

            if (_weatherWidgetOpen)
              Positioned(
                top: 48,
                right: 20,
                child: _buildWeatherTelemetryWidget(),
              ),

            // 4. Janelas Ativas na Área de Trabalho
            // Janela 1: Settings
            if (_settingsOpen)
              Positioned(
                top: _settingsMaximized ? 42 : 60,
                left: _settingsMaximized ? 20 : 140,
                child: _buildSettingsWindow(),
              ),

            // Janela 2: Q-HAL AI Sovereign Copilot (COM AS 20 FASES INTEGRADAS)
            if (_aiCopilotOpen)
              Positioned(
                top: _aiMaximized ? 42 : 70,
                right: _aiMaximized ? 20 : 340,
                child: _buildAiCopilotWindow(),
              ),

            // Janela 3: Terminal Soberano Interativo
            if (_terminalOpen)
              Positioned(
                top: _terminalMaximized ? 42 : 310,
                left: _terminalMaximized ? 20 : 170,
                child: _buildTerminalWindow(),
              ),

            // Janela 4: Q-HAL Quantum Studio 3D (Se Aberto)
            if (_qpuOpen)
              Positioned(
                top: 80,
                right: 50,
                child: _buildQHalStudioWindow(),
              ),

            // 5. Barra Superior (Top Global Status Bar)
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: _buildTopBar(),
            ),

            // 6. Menu Iniciar Flutuante com Busca Semântica Vetorial (Fase 14)
            if (_startMenuOpen)
              Positioned(
                bottom: 74,
                left: taskbarLeft,
                child: _buildStartMenu(),
              ),

            // 7. Barra de Tarefas Inferior Mais Esticada e Cantos Suaves
            Positioned(
              bottom: 12,
              left: taskbarLeft,
              child: _buildBottomTaskbar(taskbarWidth),
            ),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // BOTÕES ORIGINAIS DO BAKEN OS (WINDOW CONTROL CAPSULE EXCLUSIVO)
  // ===========================================================================
  Widget _buildBakenWindowControls({
    required VoidCallback onClose,
    required VoidCallback onMinimize,
    required VoidCallback onMaximize,
    bool isMaximized = false,
    bool isDark = false,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: isDark ? const Color(0x3300E5FF) : Colors.white.withOpacity(0.45),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isDark ? const Color(0x5500E5FF) : Colors.white.withOpacity(0.6),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _controlMicroBtn(
            icon: Icons.remove,
            tooltip: 'Minimizar',
            glowColor: const Color(0xFFF59E0B),
            onTap: onMinimize,
          ),
          const SizedBox(width: 5),
          _controlMicroBtn(
            icon: isMaximized ? Icons.fullscreen_exit : Icons.crop_square,
            tooltip: isMaximized ? 'Restaurar' : 'Maximizar',
            glowColor: const Color(0xFF00E5FF),
            onTap: onMaximize,
          ),
          const SizedBox(width: 5),
          _controlMicroBtn(
            icon: Icons.close,
            tooltip: 'Fechar',
            glowColor: const Color(0xFFF43F5E),
            isClose: true,
            onTap: onClose,
          ),
        ],
      ),
    );
  }

  Widget _controlMicroBtn({
    required IconData icon,
    required String tooltip,
    required Color glowColor,
    bool isClose = false,
    required VoidCallback onTap,
  }) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(5),
        child: Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: glowColor.withOpacity(0.2),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: glowColor.withOpacity(0.6), width: 0.8),
            boxShadow: [
              BoxShadow(color: glowColor.withOpacity(0.25), blurRadius: 4, spreadRadius: 0.5),
            ],
          ),
          child: Center(
            child: Icon(
              icon,
              size: 10,
              color: isClose ? const Color(0xFFF43F5E) : glowColor,
            ),
          ),
        ),
      ),
    );
  }

  // ===========================================================================
  // TOP BAR (BARRA SUPERIOR ELEGANTE COM STATUS DAS FASES 13-20)
  // ===========================================================================
  Widget _buildTopBar() {
    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.35),
            border: Border(
              bottom: BorderSide(color: Colors.white.withOpacity(0.5), width: 1),
            ),
          ),
          child: Row(
            children: [
              _buildVortexLogo(size: 20),
              const SizedBox(width: 8),
              const Text(
                'Baken OS',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFF1E293B)),
              ),
              const SizedBox(width: 18),
              _topBarItem('File'),
              _topBarItem('Edit'),
              _topBarItem('View'),
              _topBarItem('Q-HAL AI (Phases 1-20)'),
              const Spacer(),

              // Badges Rápidas de Status do Kernel
              _topBadge('QN-Bus: ${_qnBusLatencyNs}ns', const Color(0xFF00E5FF)),
              const SizedBox(width: 6),
              _topBadge('DynaJIT: +64%', const Color(0xFF10B981)),
              const SizedBox(width: 6),
              _topBadge('Boot: ${_instantBootMs}ms', const Color(0xFF8B5CF6)),
              const SizedBox(width: 12),

              // Botão do Assistente de Voz
              InkWell(
                onTap: _toggleVoiceAssistant,
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: _voiceListening ? const Color(0xFFEF4444).withOpacity(0.2) : const Color(0x3300E5FF),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: _voiceListening ? const Color(0xFFEF4444) : const Color(0x6600E5FF)),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _voiceListening ? Icons.mic : Icons.mic_none,
                        size: 13,
                        color: _voiceListening ? const Color(0xFFEF4444) : const Color(0xFF0284C7),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        _voiceListening ? 'Listening...' : 'Voice',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: _voiceListening ? const Color(0xFFEF4444) : const Color(0xFF0284C7),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(width: 12),
              Icon(Icons.battery_charging_full, size: 16, color: const Color(0xFF334155).withOpacity(0.85)),
              const SizedBox(width: 12),
              Icon(Icons.wifi, size: 16, color: const Color(0xFF334155).withOpacity(0.85)),
              const SizedBox(width: 14),
              const Text('ENG', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF334155))),
              const SizedBox(width: 14),
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text('10:36 AM', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
                  Text('26/08/2026', style: TextStyle(fontSize: 8.5, color: const Color(0xFF475569).withOpacity(0.8))),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _topBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withOpacity(0.5), width: 0.8),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: color),
      ),
    );
  }

  Widget _topBarItem(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6),
      child: InkWell(
        onTap: () {
          if (title.contains('Q-HAL')) {
            setState(() => _aiCopilotOpen = !_aiCopilotOpen);
          }
        },
        borderRadius: BorderRadius.circular(4),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
          child: Text(
            title,
            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w500, color: Color(0xFF334155)),
          ),
        ),
      ),
    );
  }

  // ===========================================================================
  // BOTTOM TASKBAR (DOCK ESTICADA COM CANTOS RETOS SUAVES)
  // ===========================================================================
  Widget _buildBottomTaskbar(double width) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
        child: Container(
          width: width,
          height: 52,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.45),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white.withOpacity(0.7), width: 1.2),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.08),
                blurRadius: 20,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            children: [
              // Botão Iniciar
              InkWell(
                onTap: () {
                  setState(() => _startMenuOpen = !_startMenuOpen);
                },
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: _startMenuOpen ? const Color(0x3300E5FF) : Colors.white.withOpacity(0.4),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: _startMenuOpen ? const Color(0xFF00E5FF) : Colors.white.withOpacity(0.6),
                      width: 1.2,
                    ),
                  ),
                  child: Center(
                    child: _buildVortexLogo(size: 24),
                  ),
                ),
              ),

              const SizedBox(width: 8),

              // Ícones da Taskbar
              _taskbarAppIcon(
                icon: Icons.auto_awesome,
                gradient: const [Color(0xFF00E5FF), Color(0xFF8B5CF6)],
                isActive: _aiCopilotOpen,
                onTap: () => setState(() => _aiCopilotOpen = !_aiCopilotOpen),
              ),
              _taskbarAppIcon(
                icon: Icons.terminal,
                gradient: const [Color(0xFF0F172A), Color(0xFF334155)],
                isActive: _terminalOpen,
                onTap: () => setState(() => _terminalOpen = !_terminalOpen),
              ),
              _taskbarAppIcon(
                icon: Icons.blur_on,
                gradient: const [Color(0xFF00E5FF), Color(0xFF3B82F6)],
                isActive: _qpuOpen,
                onTap: () => setState(() => _qpuOpen = !_qpuOpen),
              ),
              _taskbarAppIcon(
                icon: Icons.settings,
                gradient: const [Color(0xFFF1F5F9), Color(0xFFCBD5E1)],
                iconColor: const Color(0xFF0284C7),
                isActive: _settingsOpen,
                onTap: () => setState(() => _settingsOpen = !_settingsOpen),
              ),
              _taskbarAppIcon(
                icon: Icons.shopping_bag,
                gradient: const [Color(0xFFF59E0B), Color(0xFFFBBF24)],
                isActive: true,
                onTap: () {
                  setState(() {
                    _aiCopilotOpen = true;
                    _activeAiTab = 3; // BakenPKG
                  });
                },
              ),
              _taskbarAppIcon(
                icon: Icons.shield,
                gradient: const [Color(0xFF10B981), Color(0xFF34D399)],
                isActive: true,
                onTap: () => _handleCommand('pqc shield'),
              ),

              const Spacer(),

              _taskbarActionIcon(Icons.search, () {
                setState(() => _startMenuOpen = true);
              }),
              _taskbarActionIcon(Icons.crop_square, () {}),
              _taskbarActionIcon(Icons.notifications_none, () {}),
              _taskbarActionIcon(Icons.mic, _toggleVoiceAssistant),

              const SizedBox(width: 8),
              Container(width: 1, height: 26, color: Colors.black.withOpacity(0.12)),
              const SizedBox(width: 8),

              // Perfil do Usuário
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.35),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.white.withOpacity(0.5)),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 13,
                      backgroundColor: const Color(0xFFC084FC),
                      child: const Icon(Icons.person, size: 15, color: Colors.white),
                    ),
                    const SizedBox(width: 8),
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Elisabet Kin',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF1E293B)),
                        ),
                        Text(
                          'Ring 0 Sovereign',
                          style: TextStyle(fontSize: 8.5, color: const Color(0xFF475569).withOpacity(0.8)),
                        ),
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

  Widget _taskbarAppIcon({
    required IconData icon,
    required List<Color> gradient,
    Color iconColor = Colors.white,
    bool isActive = false,
    required VoidCallback onTap,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 36,
              height: 34,
              decoration: BoxDecoration(
                gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: gradient),
                borderRadius: BorderRadius.circular(8),
                boxShadow: [
                  BoxShadow(
                    color: gradient.first.withOpacity(0.3),
                    blurRadius: 5,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Icon(icon, size: 18, color: iconColor),
            ),
            const SizedBox(height: 2),
            Container(
              width: 4,
              height: 4,
              decoration: BoxDecoration(
                color: isActive ? const Color(0xFF0284C7) : Colors.transparent,
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _taskbarActionIcon(IconData icon, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 3),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.all(5),
          child: Icon(icon, size: 15, color: const Color(0xFF334155)),
        ),
      ),
    );
  }

  // ===========================================================================
  // Q-HAL AI SOVEREIGN COPILOT WINDOW (COM CONTROLE DAS FASES 1 A 20)
  // ===========================================================================
  Widget _buildAiCopilotWindow() {
    return _buildGlassWindow(
      width: _aiMaximized ? MediaQuery.of(context).size.width - 40 : 580,
      height: _aiMaximized ? MediaQuery.of(context).size.height - 120 : 500,
      title: 'Q-HAL Sovereign AI Core — Phases 1 to 20 Complete',
      isDark: false,
      isMaximized: _aiMaximized,
      onMinimize: () => setState(() => _aiCopilotOpen = false),
      onMaximize: () => setState(() => _aiMaximized = !_aiMaximized),
      onClose: () => setState(() => _aiCopilotOpen = false),
      child: Container(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            // Cabeçalho da IA Viva: Holo-Orb + Telemetria
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    const Color(0xFF0F172A).withOpacity(0.85),
                    const Color(0xFF1E1B4B).withOpacity(0.85),
                  ],
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.4)),
              ),
              child: Row(
                children: [
                  SizedBox(
                    width: 44,
                    height: 44,
                    child: AnimatedBuilder(
                      animation: _orbAnimCtrl,
                      builder: (context, child) {
                        return CustomPaint(
                          painter: LivingHoloOrbPainter(
                            progress: _orbAnimCtrl.value,
                            isThinking: _aiIsThinking,
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              'Q-HAL NEURAL ORB (FASES 1-20)',
                              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF00E5FF)),
                            ),
                            Text(
                              _aiIsThinking ? '● INFERINDO AVX-512' : '● RING 0 SOVEREIGN',
                              style: TextStyle(
                                fontSize: 8.5,
                                fontWeight: FontWeight.bold,
                                color: _aiIsThinking ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 3),
                        Text(
                          'QN-Bus: ${_qnBusLatencyNs}ns | DynaJIT: +64% | Boot: ${_instantBootMs}ms | Desfrag: ${_kernelMemoryDefragRate.toStringAsFixed(1)}%',
                          style: const TextStyle(fontSize: 8.5, color: Color(0xFF94A3B8)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // Abas das 20 Fases
            Container(
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.5),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white.withOpacity(0.7)),
              ),
              child: Row(
                children: [
                  _aiTabBtn(0, 'Chat'),
                  _aiTabBtn(1, 'Ring 0 IPC'),
                  _aiTabBtn(2, 'QN-Bus & JIT'),
                  _aiTabBtn(3, 'VectorFS & PKG'),
                  _aiTabBtn(4, 'Zero-Trust'),
                  _aiTabBtn(5, 'Mesh & QPU'),
                ],
              ),
            ),
            const SizedBox(height: 8),

            // Conteúdo
            Expanded(
              child: _activeAiTab == 0
                  ? _buildAiChatTab()
                  : _activeAiTab == 1
                      ? _buildAiKernelIpcTab()
                      : _activeAiTab == 2
                          ? _buildAiQnBusDynaJitTab()
                          : _activeAiTab == 3
                              ? _buildAiVectorFsPkgTab()
                              : _activeAiTab == 4
                                  ? _buildAiZeroTrustBridgeTab()
                                  : _buildAiMeshQpuTab(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _aiTabBtn(int idx, String title) {
    final isSel = _activeAiTab == idx;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _activeAiTab = idx),
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 4),
          decoration: BoxDecoration(
            color: isSel ? const Color(0xFF0284C7) : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Center(
            child: Text(
              title,
              style: TextStyle(
                fontSize: 8,
                fontWeight: isSel ? FontWeight.bold : FontWeight.w500,
                color: isSel ? Colors.white : const Color(0xFF334155),
              ),
            ),
          ),
        ),
      ),
    );
  }

  // Aba 0: Chat
  Widget _buildAiChatTab() {
    return Column(
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _aiPromptChip('⚡ Par Bell', () => _handleAiQuery('otimizar circuito bell')),
              const SizedBox(width: 6),
              _aiPromptChip('🛡️ Auditar PQC', () => _handleAiQuery('auditar chaves PQC e integridade')),
              const SizedBox(width: 6),
              _aiPromptChip('📝 Teletransporte BKN', () => _handleAiQuery('gerar codigo de teletransporte quântico em bkn')),
              const SizedBox(width: 6),
              _aiPromptChip('🚀 InstantBoot', () => _handleAiQuery('relatório de inicialização instantânea do sistema')),
            ],
          ),
        ),
        const SizedBox(height: 6),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.4),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.6)),
            ),
            child: ListView.builder(
              controller: _aiScrollCtrl,
              itemCount: _aiChatHistory.length,
              itemBuilder: (context, idx) {
                final msg = _aiChatHistory[idx];
                final isUser = msg['role'] == 'user';

                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    padding: const EdgeInsets.all(10),
                    constraints: const BoxConstraints(maxWidth: 440),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF0284C7) : Colors.white.withOpacity(0.85),
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 6, offset: const Offset(0, 2)),
                      ],
                    ),
                    child: Text(
                      msg['text']!,
                      style: TextStyle(
                        fontSize: 11,
                        color: isUser ? Colors.white : const Color(0xFF1E293B),
                        height: 1.4,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        if (_aiIsThinking)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: const [
                SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2)),
                SizedBox(width: 8),
                Text('Q-HAL AI processando tensores na GPU / AVX-512...', style: TextStyle(fontSize: 10, color: Color(0xFF0284C7))),
              ],
            ),
          ),
        const SizedBox(height: 6),
        Row(
          children: [
            Expanded(
              child: Container(
                height: 38,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.7),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.6)),
                ),
                child: TextField(
                  controller: _aiInputCtrl,
                  decoration: const InputDecoration(
                    hintText: 'Converse com o Q-HAL AI ou envie comandos para o Kernel...',
                    hintStyle: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                    border: InputBorder.none,
                    isDense: true,
                  ),
                  style: const TextStyle(fontSize: 11.5),
                  onSubmitted: _handleAiQuery,
                ),
              ),
            ),
            const SizedBox(width: 8),
            InkWell(
              onTap: () => _handleAiQuery(_aiInputCtrl.text),
              borderRadius: BorderRadius.circular(10),
              child: Container(
                height: 38,
                width: 38,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(colors: [Color(0xFF00E5FF), Color(0xFF3B82F6)]),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.arrow_upward, color: Colors.white, size: 18),
              ),
            ),
          ],
        ),
      ],
    );
  }

  // Aba 1: Ring 0 IPC
  Widget _buildAiKernelIpcTab() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('🔌 Ponte de Controle Direto do Microkernel (Ring 0 IPC)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          _metricRow('Status do Enclave PQC:', _pqcStatus, const Color(0xFF10B981)),
          _metricRow('Vazão Computacional AVX-512:', '${_avxThroughputGFlops.toStringAsFixed(1)} GFlops', const Color(0xFF0284C7)),
          _metricRow('Eficiência de Desfragmentação:', '${_kernelMemoryDefragRate.toStringAsFixed(1)}%', const Color(0xFF8B5CF6)),
          _metricRow('Coprocessador Q-HAL Ativo:', '$_activeQubits Qubits Simulados', const Color(0xFF0284C7)),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () {
              setState(() {
                _kernelMemoryDefragRate = 100.0;
                _avxThroughputGFlops = 195.2;
              });
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('⚡ Otimização do Kernel executada: Desfragmentação a 100%.')),
              );
            },
            icon: const Icon(Icons.speed, size: 14),
            label: const Text('Otimizar Ring 0', style: TextStyle(fontSize: 10.5)),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7), foregroundColor: Colors.white),
          ),
        ],
      ),
    );
  }

  // Aba 2: QN-Bus & DynaJIT (Fases 13, 15, 17)
  Widget _buildAiQnBusDynaJitTab() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('⚡ Barramento QN-Bus & BKN DynaJIT (Fases 13, 15 & 17)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          _metricRow('Latência Média QN-Bus (L3 Cache):', '$_qnBusLatencyNs ns (< 50ns Target)', const Color(0xFF10B981)),
          _metricRow('Aceleração Especulativa DynaJIT:', '+64% (${_dynaJitSpeedup}x Speedup)', const Color(0xFF0284C7)),
          _metricRow('Métodos Recompilados em Hotspot:', '1,420 Funções Ativas', const Color(0xFF8B5CF6)),
          _metricRow('Motor BakenFX 3D Raytracing:', '144 FPS (Refração Óptica 1.52)', const Color(0xFF10B981)),
          _metricRow('Uso da GPU pelo BakenFX:', '0.8% (Compute Shaders)', const Color(0xFF334155)),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () => _handleCommand('bknc build'),
            icon: const Icon(Icons.bolt, size: 14),
            label: const Text('Disparar DynaJIT Recompilação em Lote', style: TextStyle(fontSize: 10.5)),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7), foregroundColor: Colors.white),
          ),
        ],
      ),
    );
  }

  // Aba 3: Vector BakenFS & BakenPKG (Fases 14 & 18)
  Widget _buildAiVectorFsPkgTab() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('📂 Vector BakenFS & BakenPKG Mesh (Fases 14 & 18)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          _metricRow('Dimensões dos Vetores nos Inodes:', '384-D (Embeddings Embutidos)', const Color(0xFF0284C7)),
          _metricRow('Tempo Médio de Busca Semântica:', '8.4 ms (< 10 ms)', const Color(0xFF10B981)),
          _metricRow('Pacotes P2P Disponíveis no Registro:', '1,280 Aplicativos & Módulos', const Color(0xFF8B5CF6)),
          _metricRow('Velocidade de Download P2P Mesh:', '340.5 MB/s (Local Swarm)', const Color(0xFF10B981)),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () => _handleCommand('bkn pkg install quantum-studio'),
            icon: const Icon(Icons.download, size: 14),
            label: const Text('Instalar Pacote via BakenPKG P2P', style: TextStyle(fontSize: 10.5)),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF8B5CF6), foregroundColor: Colors.white),
          ),
        ],
      ),
    );
  }

  // Aba 4: Capabilities Zero-Trust & BakenBridge & InstantBoot (Fases 16, 19, 20)
  Widget _buildAiZeroTrustBridgeTab() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('🛡️ Zero-Trust, BakenBridge & InstantBoot (Fases 16, 19 & 20)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          _metricRow('Enclaves Sandbox Zero-Trust Ativos:', '18 Processos Isolados', const Color(0xFF10B981)),
          _metricRow('Tokens de Capability Assinados:', 'ML-DSA-65 Validado (FIPS 204)', const Color(0xFF0284C7)),
          _metricRow('BakenBridge Compatibilidade:', 'Linux ELF64 & Windows PE64 (99.5% Nativo)', const Color(0xFF8B5CF6)),
          _metricRow('Tempo de Boot Instantâneo:', '$_instantBootMs ms (< 800 ms)', const Color(0xFF10B981)),
          _metricRow('Descriptografia DMA NVMe:', 'TPM 2.0 / PQC Vault [OK]', const Color(0xFF334155)),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('🛡️ Auditoria Zero-Trust: 0 tentativas não autorizadas detectadas.')),
              );
            },
            icon: const Icon(Icons.security, size: 14),
            label: const Text('Auditar Sandbox Zero-Trust', style: TextStyle(fontSize: 10.5)),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981), foregroundColor: Colors.white),
          ),
        ],
      ),
    );
  }

  // Aba 5: Mesh & QPU Real (Fases 10 & 12)
  Widget _buildAiMeshQpuTab() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('🌐 Rede Mesh P2P & Ponte QPU Real (Fases 10 & 12)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          _metricRow('Cluster Mesh P2P Conectado:', '3 Nós (48.6 TFLOPS Total)', const Color(0xFF0284C7)),
          _metricRow('Hardware Quântico Físico:', 'IBM Quantum 127-Qubits', const Color(0xFF10B981)),
          _metricRow('Fidelidade de Portas 2Q:', '99.95%', const Color(0xFF8B5CF6)),
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.all(6),
            color: const Color(0xFF0F172A),
            child: const Text(
              'OPENQASM 3.0;\nqubit[2] q;\nh q[0]; cx q[0], q[1];',
              style: TextStyle(fontFamily: 'Consolas', fontSize: 9.5, color: Color(0xFF00E5FF)),
            ),
          ),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('⚛️ Circuito OpenQASM 3.0 exportado com sucesso.')),
              );
            },
            icon: const Icon(Icons.upload, size: 14),
            label: const Text('Exportar para QPU Real', style: TextStyle(fontSize: 10.5)),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7), foregroundColor: Colors.white),
          ),
        ],
      ),
    );
  }

  Widget _metricRow(String k, String v, Color c) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(k, style: const TextStyle(fontSize: 10, color: Color(0xFF475569))),
          Text(v, style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: c)),
        ],
      ),
    );
  }

  Widget _aiPromptChip(String label, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.6),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFF0284C7).withOpacity(0.3)),
        ),
        child: Text(label, style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: Color(0xFF0284C7))),
      ),
    );
  }

  // ===========================================================================
  // START MENU COM BUSCA SEMÂNTICA VETORIAL NATIVA (FASE 14)
  // ===========================================================================
  Widget _buildStartMenu() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
        child: Container(
          width: 560,
          height: 420,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.65),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.8), width: 1.2),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.12),
                blurRadius: 32,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 145,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      const Color(0xFFF472B6).withOpacity(0.2),
                      const Color(0xFFC084FC).withOpacity(0.2),
                    ],
                  ),
                  border: Border(right: BorderSide(color: Colors.white.withOpacity(0.5))),
                ),
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        _buildVortexLogo(size: 22),
                        const SizedBox(width: 8),
                        const Text(
                          'Baken OS',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFF1E293B)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    _startMenuNavItem(Icons.auto_awesome, 'Q-HAL AI (1-20)', true, onTap: () {
                      setState(() {
                        _aiCopilotOpen = true;
                        _startMenuOpen = false;
                      });
                    }),
                    _startMenuNavItem(Icons.settings, 'Settings', false),
                    _startMenuNavItem(Icons.shield, 'Zero-Trust Vault', false),
                    _startMenuNavItem(Icons.memory, 'DynaJIT & QN-Bus', false),
                    _startMenuNavItem(Icons.shopping_bag, 'BakenPKG Store', false),
                  ],
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Barra de Busca Semântica Vetorial
                      Container(
                        height: 38,
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.6),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.6)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.search, size: 16, color: Color(0xFF0284C7)),
                            const SizedBox(width: 8),
                            Expanded(
                              child: TextField(
                                decoration: const InputDecoration(
                                  hintText: 'Busca Semântica Vetorial no BakenFS...',
                                  hintStyle: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                                  border: InputBorder.none,
                                  isDense: true,
                                ),
                                style: const TextStyle(fontSize: 11.5),
                                onChanged: (v) => setState(() => _searchQuery = v),
                                onSubmitted: (val) {
                                  _handleCommand(val);
                                  setState(() => _startMenuOpen = false);
                                },
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: const [
                          Text('Vector BakenFS Matches', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
                          Text('384-D Inode Search', style: TextStyle(fontSize: 9, color: Color(0xFF0284C7), fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 6),

                      // Resultados Semânticos
                      Expanded(
                        child: ListView(
                          padding: EdgeInsets.zero,
                          children: _semanticResults.map((item) {
                            return _semanticResultItem(
                              item['name'],
                              item['cat'],
                              item['score'],
                              item['time'],
                            );
                          }).toList(),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _semanticResultItem(String filename, String category, double score, String time) {
    final percent = (score * 100).toStringAsFixed(1);
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: InkWell(
        onTap: () {
          _handleCommand('ai explicar arquivo $filename');
          setState(() => _startMenuOpen = false);
        },
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.5),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.white.withOpacity(0.6)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFF0284C7).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(Icons.insert_drive_file, size: 14, color: Color(0xFF0284C7)),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(filename, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
                    Text('$category • $time', style: const TextStyle(fontSize: 8.5, color: Color(0xFF64748B))),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFF10B981).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '$percent%',
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Color(0xFF10B981)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _startMenuNavItem(IconData icon, String title, bool isSelected, {VoidCallback? onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        margin: const EdgeInsets.only(bottom: 4),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white.withOpacity(0.5) : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          children: [
            Icon(icon, size: 13, color: isSelected ? const Color(0xFF0284C7) : const Color(0xFF475569)),
            const SizedBox(width: 8),
            Text(
              title,
              style: TextStyle(
                fontSize: 10.5,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                color: isSelected ? const Color(0xFF0284C7) : const Color(0xFF475569),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // SETTINGS WINDOW
  // ===========================================================================
  Widget _buildSettingsWindow() {
    return _buildGlassWindow(
      width: _settingsMaximized ? MediaQuery.of(context).size.width - 40 : 520,
      height: _settingsMaximized ? MediaQuery.of(context).size.height - 120 : 340,
      title: 'Settings',
      isMaximized: _settingsMaximized,
      onMinimize: () => setState(() => _settingsOpen = false),
      onMaximize: () => setState(() => _settingsMaximized = !_settingsMaximized),
      onClose: () => setState(() => _settingsOpen = false),
      child: Row(
        children: [
          Container(
            width: 110,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              border: Border(right: BorderSide(color: Colors.white.withOpacity(0.5))),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Column(
                    children: [
                      _buildVortexLogo(size: 22),
                      const SizedBox(height: 4),
                      const Text('Baken OS', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _startMenuNavItem(Icons.settings, 'Settings', true),
                _startMenuNavItem(Icons.security, 'Zero-Trust', false),
                _startMenuNavItem(Icons.memory, 'DynaJIT', false),
                _startMenuNavItem(Icons.info, 'About', false),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: GridView.count(
                crossAxisCount: _settingsMaximized ? 5 : 3,
                crossAxisSpacing: 8,
                mainAxisSpacing: 8,
                children: [
                  _settingsTile(Icons.auto_awesome, 'Q-HAL AI', const Color(0xFF00E5FF)),
                  _settingsTile(Icons.speed, 'QN-Bus', const Color(0xFF0284C7)),
                  _settingsTile(Icons.bolt, 'DynaJIT', const Color(0xFF10B981)),
                  _settingsTile(Icons.folder, 'VectorFS', const Color(0xFFF59E0B)),
                  _settingsTile(Icons.shield, 'Zero-Trust', const Color(0xFFEAB308)),
                  _settingsTile(Icons.devices, 'QPU 127Q', const Color(0xFF8B5CF6)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _settingsTile(IconData icon, String label, Color iconColor) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.6),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withOpacity(0.8)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 20, color: iconColor),
          const SizedBox(height: 3),
          Text(label, style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600, color: Color(0xFF334155))),
        ],
      ),
    );
  }

  // ===========================================================================
  // TERMINAL WINDOW
  // ===========================================================================
  Widget _buildTerminalWindow() {
    return _buildGlassWindow(
      width: _terminalMaximized ? MediaQuery.of(context).size.width - 40 : 520,
      height: _terminalMaximized ? MediaQuery.of(context).size.height - 120 : 290,
      title: 'Terminal Soberano — Ring 0 Microkernel',
      isDark: true,
      isMaximized: _terminalMaximized,
      onMinimize: () => setState(() => _terminalOpen = false),
      onMaximize: () => setState(() => _terminalMaximized = !_terminalMaximized),
      onClose: () => setState(() => _terminalOpen = false),
      child: Container(
        color: const Color(0xEB0A0F1D),
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'ARCH: x86_64 | STATUS: RING 0 SOVEREIGN | QN-BUS: 42ns | 120 FPS',
                style: TextStyle(fontSize: 8, color: Color(0xFF38BDF8), fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 6),

            Expanded(
              child: ListView.builder(
                itemCount: _termLines.length,
                itemBuilder: (context, idx) {
                  final line = _termLines[idx];
                  Color c = const Color(0xFF94A3B8);
                  if (line['type'] == 'sys') c = const Color(0xFF38BDF8);
                  if (line['type'] == 'input') c = const Color(0xFF00E5FF);
                  if (line['type'] == 'success') c = const Color(0xFF34D399);
                  if (line['type'] == 'err') c = const Color(0xFFF87171);
                  if (line['type'] == 'info') c = const Color(0xFFFBBF24);

                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 1),
                    child: Text(line['text']!, style: TextStyle(fontFamily: 'Consolas', fontSize: 10, color: c)),
                  );
                },
              ),
            ),

            const Divider(color: Color(0xFF1E293B), height: 6),

            Row(
              children: [
                const Text(
                  'baken@ring0:~\$ ',
                  style: TextStyle(fontFamily: 'Consolas', fontSize: 10.5, fontWeight: FontWeight.bold, color: Color(0xFF00E5FF)),
                ),
                Expanded(
                  child: TextField(
                    controller: _termCtrl,
                    focusNode: _termFocus,
                    onSubmitted: _handleCommand,
                    style: const TextStyle(fontFamily: 'Consolas', fontSize: 10.5, color: Colors.white),
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

  // ===========================================================================
  // Q-HAL 3D STUDIO
  // ===========================================================================
  Widget _buildQHalStudioWindow() {
    return _buildGlassWindow(
      width: 400,
      height: 350,
      title: 'Q-HAL 3D Quantum Coprocessor',
      isDark: true,
      onMinimize: () => setState(() => _qpuOpen = false),
      onMaximize: () {},
      onClose: () => setState(() => _qpuOpen = false),
      child: Container(
        color: const Color(0xEB070D18),
        padding: const EdgeInsets.all(10),
        child: Column(
          children: [
            Expanded(
              child: CustomPaint(
                painter: BlochSphere3DPainter(theta: _theta, phi: _phi),
                child: Container(),
              ),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.3)),
              ),
              child: Column(
                children: [
                  _telemetryRow('Estado:', _activeStateName, const Color(0xFF00E5FF)),
                  const SizedBox(height: 2),
                  _telemetryRow('Fidelidade:', '$_fidelity%', const Color(0xFF34D399)),
                  _telemetryRow('QN-Bus Latência:', '${_qnBusLatencyNs}ns [L3 Direct]', const Color(0xFFC084FC)),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _handleCommand('qpu bell'),
                    icon: const Icon(Icons.hub, size: 11),
                    label: const Text('Par Bell', style: TextStyle(fontSize: 9)),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0x3300E5FF), foregroundColor: const Color(0xFF00E5FF)),
                  ),
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _handleAiQuery('otimizar circuito quantico bell'),
                    icon: const Icon(Icons.auto_awesome, size: 11),
                    label: const Text('Otimizar IA', style: TextStyle(fontSize: 9)),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0x338B5CF6), foregroundColor: const Color(0xFFC084FC)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _telemetryRow(String k, String v, Color c) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(k, style: const TextStyle(fontSize: 9, color: Colors.white54)),
        Text(v, style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: c)),
      ],
    );
  }

  // ===========================================================================
  // WIDGETS DO DESKTOP (CALENDÁRIO & TEMPO)
  // ===========================================================================
  Widget _buildCalendarWidget() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
        child: Container(
          width: 125,
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.55),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white.withOpacity(0.7)),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 14, offset: const Offset(0, 4)),
            ],
          ),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: const [
                  Text('Baken OS', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold)),
                  Icon(Icons.chevron_right, size: 11),
                ],
              ),
              const SizedBox(height: 4),
              const Text('Su Mo Tu We Th Fr Sa', style: TextStyle(fontSize: 6.5, color: Color(0xFF64748B))),
              const SizedBox(height: 3),
              _calendarRow(['2', '3', '4', '5', '6', '7', '8'], highlight: '7'),
              _calendarRow(['9', '10', '11', '12', '13', '14', '15']),
              _calendarRow(['16', '17', '18', '19', '20', '21', '22']),
            ],
          ),
        ),
      ),
    );
  }

  Widget _calendarRow(List<String> days, {String? highlight}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: days.map((d) {
          final isHigh = (d == highlight);
          return Container(
            width: 11,
            height: 11,
            decoration: BoxDecoration(
              color: isHigh ? const Color(0xFF0284C7) : Colors.transparent,
              borderRadius: BorderRadius.circular(2.5),
            ),
            child: Center(
              child: Text(
                d,
                style: TextStyle(
                  fontSize: 6.5,
                  fontWeight: isHigh ? FontWeight.bold : FontWeight.normal,
                  color: isHigh ? Colors.white : const Color(0xFF334155),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildWeatherTelemetryWidget() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
        child: Container(
          width: 125,
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.55),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white.withOpacity(0.7)),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 14, offset: const Offset(0, 4)),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: const [
                  Icon(Icons.wb_sunny, color: Color(0xFFF59E0B), size: 18),
                  Text('33°F', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF1E293B))),
                ],
              ),
              const SizedBox(height: 6),
              Text('QN-Bus: ${_qnBusLatencyNs}ns', style: const TextStyle(fontSize: 7.5, color: Color(0xFF10B981), fontWeight: FontWeight.bold)),
              Text('Boot: ${_instantBootMs}ms', style: const TextStyle(fontSize: 7.5, color: Color(0xFF0284C7))),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDesktopFolder({
    required double x,
    required double y,
    required String label,
    required List<Color> iconGradient,
    bool hasVortex = false,
  }) {
    return Positioned(
      left: x,
      top: y,
      child: Column(
        children: [
          Container(
            width: 48,
            height: 40,
            decoration: BoxDecoration(
              gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: iconGradient),
              borderRadius: BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: iconGradient.first.withOpacity(0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Stack(
              children: [
                if (hasVortex)
                  Center(child: _buildVortexLogo(size: 20))
                else
                  const Center(child: Icon(Icons.folder, color: Colors.white, size: 22)),
              ],
            ),
          ),
          const SizedBox(height: 3),
          Text(
            label,
            style: const TextStyle(
              fontSize: 9.5,
              fontWeight: FontWeight.w600,
              color: Colors.white,
              shadows: [Shadow(color: Colors.black45, blurRadius: 4, offset: Offset(0, 1))],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGlassWindow({
    required double width,
    required double height,
    required String title,
    required Widget child,
    bool isDark = false,
    bool isMaximized = false,
    required VoidCallback onClose,
    required VoidCallback onMinimize,
    required VoidCallback onMaximize,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 30, sigmaY: 30),
        child: Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            color: isDark ? const Color(0xEB0D1322) : Colors.white.withOpacity(0.75),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isDark ? const Color(0xFF00E5FF).withOpacity(0.4) : Colors.white.withOpacity(0.85),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.12),
                blurRadius: 28,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            children: [
              Container(
                height: 34,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B).withOpacity(0.6) : Colors.white.withOpacity(0.4),
                  border: Border(bottom: BorderSide(color: Colors.white.withOpacity(0.4))),
                ),
                child: Row(
                  children: [
                    _buildBakenWindowControls(
                      onClose: onClose,
                      onMinimize: onMinimize,
                      onMaximize: onMaximize,
                      isMaximized: isMaximized,
                      isDark: isDark,
                    ),
                    const SizedBox(width: 12),
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.bold,
                        color: isDark ? const Color(0xFF00E5FF) : const Color(0xFF1E293B),
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

  Widget _buildVortexLogo({required double size}) {
    return AnimatedBuilder(
      animation: _vortexAnimCtrl,
      builder: (context, child) {
        return Transform.rotate(
          angle: _vortexAnimCtrl.value * 2 * math.pi,
          child: Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const SweepGradient(
                colors: [
                  Color(0xFF00E5FF),
                  Color(0xFF818CF8),
                  Color(0xFFE879F9),
                  Color(0xFF00E5FF),
                ],
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00E5FF).withOpacity(0.4),
                  blurRadius: 6,
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.all(2),
              child: Container(
                decoration: const BoxDecoration(shape: BoxShape.circle, color: Color(0xFF060913)),
                child: Center(
                  child: Container(
                    width: size * 0.35,
                    height: size * 0.35,
                    decoration: const BoxDecoration(shape: BoxShape.circle, color: Color(0xFF00E5FF)),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

// ===========================================================================
// LIVING Q-HAL NEURAL HOLO-ORB PAINTER
// ===========================================================================
class LivingHoloOrbPainter extends CustomPainter {
  final double progress;
  final bool isThinking;

  LivingHoloOrbPainter({required this.progress, required this.isThinking});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final radius = size.width * 0.42;

    final pulseScale = 1.0 + (isThinking ? math.sin(progress * math.pi * 4) * 0.15 : math.sin(progress * math.pi * 2) * 0.08);
    final glowPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          (isThinking ? const Color(0xFFF59E0B) : const Color(0xFF00E5FF)).withOpacity(0.4),
          Colors.transparent,
        ],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: radius * 1.5 * pulseScale));
    canvas.drawCircle(Offset(cx, cy), radius * 1.4 * pulseScale, glowPaint);

    final corePaint = Paint()
      ..shader = RadialGradient(
        colors: [
          Colors.white,
          isThinking ? const Color(0xFFF59E0B) : const Color(0xFF00E5FF),
          const Color(0xFF8B5CF6),
        ],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: radius));
    canvas.drawCircle(Offset(cx, cy), radius * 0.6, corePaint);

    final filamentPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;

    for (int i = 0; i < 3; i++) {
      final angleOffset = (i * math.pi / 1.5) + (progress * 2 * math.pi * (isThinking ? 2.5 : 1.0));
      final ringColor = i == 0
          ? const Color(0xFF00E5FF)
          : (i == 1 ? const Color(0xFFE879F9) : const Color(0xFF8B5CF6));

      filamentPaint.color = ringColor.withOpacity(0.8);
      canvas.save();
      canvas.translate(cx, cy);
      canvas.rotate(angleOffset);
      canvas.drawOval(
        Rect.fromCenter(center: Offset.zero, width: radius * 1.9, height: radius * 0.65),
        filamentPaint,
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant LivingHoloOrbPainter oldDelegate) => true;
}

// ===========================================================================
// BLOCH SPHERE 3D PAINTER
// ===========================================================================
class BlochSphere3DPainter extends CustomPainter {
  final double theta;
  final double phi;

  BlochSphere3DPainter({required this.theta, required this.phi});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final radius = math.min(cx, cy) * 0.78;

    final spherePaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.3, -0.3),
        colors: [
          const Color(0xFF00E5FF).withOpacity(0.25),
          const Color(0xFF070F1E).withOpacity(0.8),
        ],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: radius));
    canvas.drawCircle(Offset(cx, cy), radius, spherePaint);

    final borderPaint = Paint()
      ..color = const Color(0xFF00E5FF).withOpacity(0.4)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    canvas.drawCircle(Offset(cx, cy), radius, borderPaint);

    canvas.drawOval(
      Rect.fromCenter(center: Offset(cx, cy), width: radius * 2, height: radius * 0.6),
      borderPaint..color = const Color(0xFF818CF8).withOpacity(0.3),
    );

    final axisPaint = Paint()
      ..color = Colors.white24
      ..strokeWidth = 1;
    canvas.drawLine(Offset(cx, cy - radius - 10), Offset(cx, cy + radius + 10), axisPaint);
    canvas.drawLine(Offset(cx - radius - 10, cy), Offset(cx + radius + 10, cy), axisPaint);

    final vx = cx + radius * math.sin(theta) * math.cos(phi);
    final vy = cy - radius * math.cos(theta);

    final vectorPaint = Paint()
      ..color = const Color(0xFF00E5FF)
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(Offset(cx, cy), Offset(vx, vy), vectorPaint);

    canvas.drawCircle(Offset(vx, vy), 5, Paint()..color = const Color(0xFF00E5FF));
    canvas.drawCircle(Offset(vx, vy), 2, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(covariant BlochSphere3DPainter oldDelegate) =>
      oldDelegate.theta != theta || oldDelegate.phi != phi;
}
