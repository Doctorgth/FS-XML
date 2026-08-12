using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public class FSXMLLauncher {
    // Импорт функций из WinAPI для загрузки библиотек
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    private static extern IntPtr LoadLibrary(string lpFileName);

    [DllImport("kernel32.dll", CharSet = CharSet.Ansi, ExactSpelling = true, SetLastError = true)]
    private static extern IntPtr GetProcAddress(IntPtr hModule, string procName);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetDllDirectory(string lpPathName);

    // Описываем сигнатуру функции Py_Main из python312.dll
    [UnmanagedFunctionPointer(CallingConvention.Cdecl, CharSet = CharSet.Unicode)]
    private delegate int Py_Main(int argc, [MarshalAs(UnmanagedType.LPArray, ArraySubType = UnmanagedType.LPWStr)] string[] argv);

    [STAThread]
    public static void Main() {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        
        // Корректный рабочий каталог
        Directory.SetCurrentDirectory(baseDir);
        
        string pythonDir = Path.Combine(baseDir, "python");
        
        // Укажите точное имя вашей DLL (например, python312.dll или другую версию)
        string dllName = "python312.dll"; 
        string pythonDllPath = Path.Combine(pythonDir, dllName);

        if (!File.Exists(pythonDllPath)) {
            MessageBox.Show("Критическая ошибка: Не найден файл " + dllName + " в папке 'python'.", "FS-XML");
            return;
        }

        // 1. Добавляем папку python в пути поиска DLL
        SetDllDirectory(pythonDir);

        // 2. Загружаем библиотеку Python
        IntPtr hPython = LoadLibrary(pythonDllPath);
        if (hPython == IntPtr.Zero) {
            MessageBox.Show("Не удалось загрузить ядро Python из " + dllName, "FS-XML");
            return;
        }

        // 3. Ищем точку входа Py_Main
        IntPtr pPyMain = GetProcAddress(hPython, "Py_Main");
        if (pPyMain == IntPtr.Zero) {
            MessageBox.Show("Ошибка: В DLL не найдена функция Py_Main.", "FS-XML");
            return;
        }

        Py_Main runPython = (Py_Main)Marshal.GetDelegateForFunctionPointer(pPyMain, typeof(Py_Main));

        // 4. Формируем аргументы
        string[] args = new string[] { "FS-XML.exe", Path.Combine(baseDir, "main.py") };

        try {
            // Вызов интерпретатора внутри текущего процесса
            runPython(args.Length, args);
        } catch (Exception ex) {
            MessageBox.Show("Ошибка выполнения скрипта: " + ex.Message, "FS-XML");
        }
    }
}