"use client"

import { useState } from "react"
import { FileUpload } from "@/components/FileUpload"
import { ProcessingStatus, type Status } from "@/components/ProcessingStatus"
import { Button } from "@/components/ui/button"
import { api, ApiError } from "@/lib/api"
import { GitCompare } from "lucide-react"

export default function ComparePage() {
  const [fileA, setFileA] = useState<File | null>(null)
  const [fileB, setFileB] = useState<File | null>(null)
  const [status, setStatus] = useState<Status>("idle")
  const [error, setError] = useState("")

  async function handleSubmit() {
    if (!fileA || !fileB) return

    setError("")
    setStatus("processing")

    try {
      const blob = await api.postTwoFiles<Blob>("/compare/docx", fileA, fileB)

      const filename = `diff_${fileA.name}_vs_${fileB.name}.docx`
      api.downloadBlob(blob, filename)

      setStatus("success")
    } catch (e) {
      setStatus("error")
      setError(e instanceof ApiError ? e.message : "Неизвестная ошибка")
    }
  }

  function handleReset() {
    setFileA(null)
    setFileB(null)
    setStatus("idle")
    setError("")
  }

  const busy = status === "processing"

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-slate-100 rounded-md">
            <GitCompare className="w-5 h-5 text-slate-700" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Сравнение документов</h1>
        </div>
        <p className="text-slate-600 ml-12">
          Загрузите две версии DOCX — получите отчёт с выделенными различиями:
          добавленное, удалённое, изменённое.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">
              Документ A (исходный)
            </label>
            <FileUpload
              file={fileA}
              onFileSelect={setFileA}
              accept=".docx"
              label="Выберите первый файл"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">
              Документ B (новая версия)
            </label>
            <FileUpload
              file={fileB}
              onFileSelect={setFileB}
              accept=".docx"
              label="Выберите второй файл"
            />
          </div>
        </div>

        <ProcessingStatus
          status={status}
          message={
            status === "processing"
              ? "Поиск различий..."
              : status === "success"
                ? "Отчёт сохранён в Загрузки"
                : undefined
          }
          error={error}
        />

        <div className="flex gap-3">
          <Button onClick={handleSubmit} disabled={!fileA || !fileB || busy}>
            {busy ? "Сравниваю..." : "Сравнить документы"}
          </Button>

          {(status === "success" || status === "error") && (
            <Button variant="outline" onClick={handleReset}>
              Новое сравнение
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

