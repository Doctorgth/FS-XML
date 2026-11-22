using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace FsXmlLauncher
{
    internal static class Program
    {
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool SetDllDirectory(string lpPathName);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr LoadLibrary(string lpFileName);

        [DllImport("kernel32.dll", CharSet = CharSet.Ansi, SetLastError = true)]
        private static extern IntPtr GetProcAddress(IntPtr hModule, string procName);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool FreeLibrary(IntPtr hModule);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        private delegate void PyInitializeDelegate();

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        private delegate int PyFinalizeExDelegate();

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        private delegate void PyFinalizeDelegate();

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        private delegate int PyRunSimpleStringDelegate(byte[] command);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        private delegate void PySetProgramNamePtrDelegate(IntPtr name);

        [STAThread]
        private static int Main(string[] args)
        {
            string rootDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');
            Environment.CurrentDirectory = rootDir;

            string pythonDir = Path.Combine(rootDir, "python");
            if (!Directory.Exists(pythonDir))
            {
                ShowError("Не найдена папка 'python' рядом с FS-XML.exe:\n" + pythonDir);
                return 1;
            }

            string pythonDll = FindPythonDll(pythonDir);
            if (string.IsNullOrEmpty(pythonDll))
            {
                ShowError("Не найдена библиотека python3XX.dll в папке:\n" + pythonDir);
                return 1;
            }

            string appScript = Path.Combine(rootDir, "desktop_app.py");
            if (!File.Exists(appScript))
            {
                ShowError("Не найден файл desktop_app.py в корне проекта:\n" + appScript);
                return 1;
            }

            string currentPath = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
            Environment.SetEnvironmentVariable("PATH", pythonDir + ";" + currentPath);
            Environment.SetEnvironmentVariable("PYTHONUTF8", "1");

            SetDllDirectory(pythonDir);

            IntPtr hPython = LoadLibrary(pythonDll);
            if (hPython == IntPtr.Zero)
            {
                int err = Marshal.GetLastWin32Error();
                ShowError(
                    "Не удалось загрузить DLL Python:\n" + pythonDll +
                    "\nКод ошибки Win32: " + err +
                    "\n\nПроверьте совпадение разрядности (x64/x86) и наличие Visual C++ Redistributable."
                );
                return 1;
            }

            IntPtr programNamePtr = IntPtr.Zero;
            try
            {
                IntPtr pInit = GetProcAddress(hPython, "Py_Initialize");
                IntPtr pRun = GetProcAddress(hPython, "PyRun_SimpleString");
                IntPtr pFinalizeEx = GetProcAddress(hPython, "Py_FinalizeEx");
                IntPtr pFinalize = GetProcAddress(hPython, "Py_Finalize");
                IntPtr pSetProgramName = GetProcAddress(hPython, "Py_SetProgramName");

                if (pInit == IntPtr.Zero || pRun == IntPtr.Zero || (pFinalizeEx == IntPtr.Zero && pFinalize == IntPtr.Zero))
                {
                    ShowError("В загруженной DLL отсутствуют необходимые экспортируемые функции Python C API.");
                    return 1;
                }

                string pythonExe = Path.Combine(pythonDir, "python.exe");
                if (pSetProgramName != IntPtr.Zero)
                {
                    string prog = File.Exists(pythonExe) ? pythonExe : System.Reflection.Assembly.GetExecutingAssembly().Location;
                    programNamePtr = Marshal.StringToHGlobalUni(prog);
                    var setProgramName = (PySetProgramNamePtrDelegate)(object)Marshal.GetDelegateForFunctionPointer(
                        pSetProgramName, typeof(PySetProgramNamePtrDelegate)
                    );
                    setProgramName(programNamePtr);
                }

                var pyInitialize = (PyInitializeDelegate)(object)Marshal.GetDelegateForFunctionPointer(
                    pInit, typeof(PyInitializeDelegate)
                );
                var pyRunSimpleString = (PyRunSimpleStringDelegate)(object)Marshal.GetDelegateForFunctionPointer(
                    pRun, typeof(PyRunSimpleStringDelegate)
                );

                Environment.SetEnvironmentVariable("FSXML_ROOT_DIR", rootDir);
                Environment.SetEnvironmentVariable("FSXML_PYTHON_EXE", pythonExe);
                Environment.SetEnvironmentVariable("FSXML_ARGS", args != null && args.Length > 0 ? string.Join("\n", args) : string.Empty);

                string errorLogPath = Path.Combine(rootDir, "launcher_error.log");
                if (File.Exists(errorLogPath))
                {
                    try { File.Delete(errorLogPath); } catch { }
                }

                pyInitialize();

                string bootstrap =
                    "import os, sys, traceback\n" +
                    "root_dir = os.environ.pop('FSXML_ROOT_DIR')\n" +
                    "python_exe = os.environ.pop('FSXML_PYTHON_EXE', '')\n" +
                    "raw_args = os.environ.pop('FSXML_ARGS', '')\n" +
                    "os.chdir(root_dir)\n" +
                    "if root_dir not in sys.path:\n" +
                    "    sys.path.insert(0, root_dir)\n" +
                    "if python_exe and os.path.isfile(python_exe):\n" +
                    "    sys.executable = python_exe\n" +
                    "if sys.stdout is None:\n" +
                    "    sys.stdout = open(os.devnull, 'w', encoding='utf-8')\n" +
                    "if sys.stderr is None:\n" +
                    "    sys.stderr = open(os.devnull, 'w', encoding='utf-8')\n" +
                    "app_script = os.path.join(root_dir, 'desktop_app.py')\n" +
                    "extra = [a for a in raw_args.split('\\n') if a] if raw_args else []\n" +
                    "sys.argv = [app_script] + extra\n" +
                    "try:\n" +
                    "    with open(app_script, 'r', encoding='utf-8') as f:\n" +
                    "        code = compile(f.read(), app_script, 'exec')\n" +
                    "    exec(code, {'__name__': '__main__', '__file__': app_script})\n" +
                    "except Exception:\n" +
                    "    try:\n" +
                    "        with open(os.path.join(root_dir, 'launcher_error.log'), 'w', encoding='utf-8') as lf:\n" +
                    "            lf.write(traceback.format_exc())\n" +
                    "    except Exception:\n" +
                    "        pass\n" +
                    "    raise\n";

                byte[] utf8 = Encoding.UTF8.GetBytes(bootstrap + "\0");
                int rc = pyRunSimpleString(utf8);

                if (pFinalizeEx != IntPtr.Zero)
                {
                    var pyFinalizeEx = (PyFinalizeExDelegate)(object)Marshal.GetDelegateForFunctionPointer(
                        pFinalizeEx, typeof(PyFinalizeExDelegate)
                    );
                    pyFinalizeEx();
                }
                else
                {
                    var pyFinalize = (PyFinalizeDelegate)(object)Marshal.GetDelegateForFunctionPointer(
                        pFinalize, typeof(PyFinalizeDelegate)
                    );
                    pyFinalize();
                }

                if (rc != 0)
                {
                    string details = File.Exists(errorLogPath)
                        ? File.ReadAllText(errorLogPath, Encoding.UTF8)
                        : "Выполнение desktop_app.py завершилось с ошибкой (код " + rc + ").";
                    ShowError("Ошибка при запуске проекта:\n\n" + details);
                    return 1;
                }

                return 0;
            }
            catch (Exception ex)
            {
                ShowError("Непредвиденная ошибка запуска:\n\n" + ex);
                return 1;
            }
            finally
            {
                if (programNamePtr != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(programNamePtr);
                }
                FreeLibrary(hPython);
            }
        }

        private static string FindPythonDll(string pythonDir)
        {
            string[] candidates = Directory.GetFiles(pythonDir, "python*.dll");
            Regex versionedRegex = new Regex(@"^python3\d+\.dll$", RegexOptions.IgnoreCase);
            foreach (string file in candidates)
            {
                string name = Path.GetFileName(file);
                if (versionedRegex.IsMatch(name))
                {
                    return file;
                }
            }

            foreach (string file in candidates)
            {
                string name = Path.GetFileName(file);
                if (!string.Equals(name, "python3.dll", StringComparison.OrdinalIgnoreCase))
                {
                    return file;
                }
            }

            return null;
        }

        private static void ShowError(string message)
        {
            MessageBox.Show(message, "FS-XML Interpreter — Ошибка", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}