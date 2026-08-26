import * as vscode from 'vscode';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
    console.log('Extensão Oficial BKN Language & Quantum Tooling ativada!');

    // Comando 1: Executar Simulador Quântico Q-HAL
    let runSimulatorCmd = vscode.commands.registerCommand('bkn.runQuantumSimulator', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('Nenhum arquivo .bkn ativo para executar.');
            return;
        }

        const terminal = vscode.window.createTerminal('Baken Q-HAL Simulator');
        terminal.show();
        terminal.sendText(`bknc --run-quantum "${editor.document.fileName}"`);
    });

    // Comando 2: Visualizador da Esfera de Bloch 3D Interativa
    let blochSphereCmd = vscode.commands.registerCommand('bkn.showBlochSphere', () => {
        const panel = vscode.window.createWebviewPanel(
            'blochSphere',
            'Baken Q-HAL: Visualizador de Esfera de Bloch',
            vscode.ViewColumn.Beside,
            { enableScripts: true }
        );

        panel.webview.html = getBlochSphereWebviewContent();
    });

    // Comando 3: Compilar para Binário Nativo .bkn_exec
    let compileBinaryCmd = vscode.commands.registerCommand('bkn.compileNative', () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const terminal = vscode.window.createTerminal('BKNC Compiler');
        terminal.show();
        terminal.sendText(`bknc --target bkn_exec --pqc-sign "${editor.document.fileName}"`);
        vscode.window.showInformationMessage('Compilação BKN iniciada com assinatura Pós-Quântica (ML-DSA).');
    });

    context.subscriptions.push(runSimulatorCmd, blochSphereCmd, compileBinaryCmd);
}

function getBlochSphereWebviewContent(): string {
    return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Esfera de Bloch Baken Q-HAL</title>
    <style>
        body {
            margin: 0;
            background: radial-gradient(circle at center, #10162A 0%, #060913 100%);
            color: #00E5FF;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
        }
        #canvas-container {
            position: relative;
            width: 320px;
            height: 320px;
        }
        canvas {
            border-radius: 50%;
            box-shadow: 0 0 50px rgba(0, 229, 255, 0.25);
        }
        .telemetry-card {
            margin-top: 20px;
            padding: 16px 24px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 229, 255, 0.3);
            border-radius: 12px;
            backdrop-filter: blur(10px);
            text-align: center;
        }
        .btn-gate {
            background: #00E5FF;
            color: #060913;
            border: none;
            padding: 8px 16px;
            margin: 4px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h2>Esfera de Bloch (Qubit |ψ⟩)</h2>
    <div id="canvas-container">
        <canvas id="blochCanvas" width="320" height="320"></canvas>
    </div>
    <div class="telemetry-card">
        <div><strong>Estado:</strong> |ψ⟩ = 0.707|0⟩ + 0.707|1⟩</div>
        <div><strong>Probabilidade P(|0⟩):</strong> 50.0% | <strong>P(|1⟩):</strong> 50.0%</div>
        <div style="margin-top: 12px;">
            <button class="btn-gate" onclick="rotateH()">H (Hadamard)</button>
            <button class="btn-gate" onclick="rotateX()">X (NOT)</button>
            <button class="btn-gate" onclick="rotateZ()">Z (Phase)</button>
        </div>
    </div>
    <script>
        const canvas = document.getElementById('blochCanvas');
        const ctx = canvas.getContext('2d');
        let theta = Math.PI / 2;
        let phi = 0;

        function drawBlochSphere() {
            ctx.clearRect(0, 0, 320, 320);
            const cx = 160, cy = 160, r = 120;

            // Círculo principal
            ctx.strokeStyle = 'rgba(0, 229, 255, 0.4)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();

            // Equador
            ctx.beginPath();
            ctx.ellipse(cx, cy, r, r * 0.35, 0, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(124, 77, 255, 0.3)';
            ctx.stroke();

            // Eixo Z
            ctx.beginPath();
            ctx.moveTo(cx, cy - r - 10);
            ctx.lineTo(cx, cy + r + 10);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.stroke();

            // Vetor de Estado Quântico
            const vx = cx + r * Math.sin(theta) * Math.cos(phi);
            const vy = cy - r * Math.cos(theta) * 0.9;
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(vx, vy);
            ctx.strokeStyle = '#00E5FF';
            ctx.lineWidth = 3;
            ctx.stroke();

            // Ponto de estado
            ctx.fillStyle = '#FF4081';
            ctx.beginPath();
            ctx.arc(vx, vy, 6, 0, Math.PI * 2);
            ctx.fill();
        }

        function rotateH() { theta = Math.PI / 2; phi = 0; drawBlochSphere(); }
        function rotateX() { theta = Math.PI - theta; drawBlochSphere(); }
        function rotateZ() { phi += Math.PI; drawBlochSphere(); }

        drawBlochSphere();
    </script>
</body>
</html>`;
}

export function deactivate() {}
