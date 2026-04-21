"use client"

import { useState } from "react"
import { FileUpload } from "@/components/FileUpload"
import { ProcessingStatus, type Status } from "@/components/ProcessingStatus"
import { Button } from "@/components/ui/button"
import { api, ApiError } from "@/lib/api"
import { Wand2 } from "lucide-react"

export default function NormalizePage() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<Status>("idle")
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState("")

  async function handleSubmit() {
    if (!file) return

    setError("")
    setStatus("uploading")
    setProgress(0)

    try {
      const blob = await api.postFile<Blob>(
        "/normalize/pptx",
        file,
        undefined,
        (p) => {
          setProgress(p)
          if (p === 100) setStatus("processing")
        },
      )

      const filename = `normalized_${file.name}`
      api.downloadBlob(blob, filename)

      setStatus("success")
    } catch (e) {
      setStatus("error")
      if (e instanceof ApiError) {
        setError(e.message)
      } else {
        setError("Неизвестная ошибка")
      }
    }
  }

  function handleReset() {
    setFile(null)
    setStatus("idle")
    setProgress(0)
    setError("")
  }

  const busy = status === "uploading" || status === "processing"

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-slate-100 rounded-md">
            <Wand2 className="w-5 h-5 text-slate-700" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Нормализация PPTX</h1>
        </div>
        <p className="text-slate-600 ml-12">
          Унификация шрифтов, размеров и цветов. Сбрасывает аномалии (чужие шрифты, аномальные размеры), сохраняет авторский стиль.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
        <FileUpload
          file={file}
          onFileSelect={setFile}
          accept=".pptx"
          maxSizeMb={50}
          label="Перетащите PPTX файл или нажмите для выбора"
        />

        <ProcessingStatus
          status={status}
          progress={progress}
          message={status === "success" ? "Файл сохранён в Загрузки" : undefined}
          error={error}
        />

        <div className="flex gap-3">
          <Button onClick={handleSubmit} disabled={!file || busy}>
            {busy ? "Обработка..." : "Нормализовать"}
          </Button>

          {(status === "success" || status === "error") && (
            <Button variant="outline" onClick={handleReset}>
              Новый файл
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

