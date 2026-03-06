' Sherry Desktop Sprite 静默启动脚本
' 双击运行，不显示控制台窗口

Option Explicit

Dim WshShell, fso, scriptDir, pythonCmd, portCheckCmd, pid

Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set WshShell = CreateObject("WScript.Shell")

' 先杀掉占用8765端口的进程
Dim exec, line, pos
Set exec = WshShell.Exec("cmd /c netstat -ano | findstr :8765")
Do While exec.Status = 0
    WScript.Sleep 100
Loop

line = exec.StdOut.ReadAll()
If Len(line) > 0 Then
    ' 提取PID并结束进程
    pos = InStrRev(line, " ")
    If pos > 0 Then
        pid = Trim(Mid(line, pos))
        WshShell.Run "taskkill /F /PID " & pid, 0, True
        WScript.Sleep 500
    End If
End If

' 启动Python程序（隐藏窗口）
WshShell.CurrentDirectory = scriptDir
WshShell.Run "python src/main.py", 0, False

' 显示提示
WshShell.PopUp "雪莉桌面精灵已启动！" & vbCrLf & vbCrLf & "WebSocket: ws://127.0.0.1:8765/sprite" & vbCrLf & vbCrLf & "提示：右键系统托盘图标可退出", 3, "Sherry Desktop Sprite", 64
