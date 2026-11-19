Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]

Add-Type @'
using System;
using System.Threading.Tasks;
using Windows.Foundation;

public static class AsyncHelper {
    public static T Await<T>(IAsyncOperation<T> asyncOp) {
        TaskCompletionSource<T> tcs = new TaskCompletionSource<T>();
        asyncOp.Completed = (info, status) => {
            if (status == AsyncStatus.Completed) tcs.SetResult(info.GetResults());
            else if (status == AsyncStatus.Error) tcs.SetException(info.ErrorCode);
            else if (status == AsyncStatus.Canceled) tcs.SetCanceled();
        };
        return tcs.Task.Result;
    }
}
'@

$path = "D:\Onoda Inc\Test Projects\python\invoice-maker\data\uploads\memos\1c34438b-5dc5-43b6-b351-7590c6239315\5dbd32730e14cf47_memo_capture.jpg"
$file = [AsyncHelper]::Await([Windows.Storage.StorageFile]::GetFileFromPathAsync($path))
$stream = [AsyncHelper]::Await($file.OpenAsync([Windows.Storage.FileAccessMode]::Read))
$decoder = [AsyncHelper]::Await([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream))
$bitmap = [AsyncHelper]::Await($decoder.GetSoftwareBitmapAsync())

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$result = [AsyncHelper]::Await($engine.RecognizeAsync($bitmap))

Write-Host "Total Lines Found:" $result.Lines.Count
$output = @()
foreach ($line in $result.Lines) {
    Write-Host "LINE: $($line.Text)"
}
