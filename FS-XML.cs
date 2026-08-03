using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

class Program
{
    [STAThread]
    static void Main()
    {
        string currentDir = AppDomain.CurrentDomain.BaseDirectory;
        // Путь к переносимому pythonw.exe (запускает без черного окна консоли)
        string pythonPath = Path.Combine(currentDir, "python", "pythonw.exe");
        // Путь к вашему main.py
        string scriptPath = Path.Combine(currentDir, "main.py");

        if (!File.Exists(pythonPath))
        {
            MessageBox.Show("Не найден интерпретатор Python в папке 'python'.", "Ошибка запуска", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        if (!File.Exists(scriptPath))
        {
            MessageBox.Show("Не найден файл скрипта 'main.py'.", "Ошибка запуска", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        ProcessStartInfo startInfo = new ProcessStartInfo();
        startInfo.FileName = pythonPath;
        // Передаем main.py как аргумент в кавычках
        startInfo.Arguments = "\"" + scriptPath + "\"";
        startInfo.WorkingDirectory = currentDir;
        startInfo.UseShellExecute = false;
        startInfo.CreateNoWindow = true; // Скрываем консоль

        try
        {
            Process.Start(startInfo);
        }
        catch (Exception ex)
        {
            MessageBox.Show("Не удалось запустить приложение: " + ex.Message, "Ошибка", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}