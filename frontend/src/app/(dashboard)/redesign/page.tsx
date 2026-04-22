"use client"

import { useState } from "react"
import { FileUpload } from "@/components/FileUpload"
import { ProcessingStatus, type Status } from "@/components/ProcessingStatus"
import { Button } from "@/components/ui/button"
import { api, ApiError } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Palette } from "lucide-react"

type StyleId = "formal" | "corporate" | "bold"

interface StyleOption {
  id: StyleId
  name: string
  description: string
  colors: [string, string]
  font: string
}

// Синхронно с GET /redesign/styles (backend/main.py).
// Захардкожено намеренно — экономит fetch при первом рендере.
// Если набор стилей расширится — заменить на useEffect + fetch.
const STYLES: StyleOption[] = [
  {
    id: "formal",
    name: "Формальный",
    description: "Классика. Для судов, меморандумов.",
    colors: ["#253278", "#F8EFE5"],
    font: "Inter",
  },
  {
    id: "corporate",
    name: "Корпоративный",
    description: "Чистый с градиентами. Для клиентов.",
    colors: ["#24629A", "#E8A46B"],
    font: "Lato + Source Serif",
  },
  {
    id: "bold",
    name: "Современный",
    description: "Тёмный контраст. Для питчей.",
    colors: ["#000000", "#2D8FCF"],
    font: "Kollektif",
  },
]

export default function RedesignPage() {
  const [file, setFile] = useState<File | null>(null)
  const [style, setStyle] = useState<StyleId>("formal")
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
        "/redesign/pptx",
        file,
        { style },
        (p) => {
          setProgress(p)
          if (p === 100) setStatus("processing")
        },
      )

      const filename = `redesigned_${style}_${file.name}`
      api.downloadBlob(blob, filename)
      setStatus("success")
    } catch (e) {
      setStatus("error")
      setError(e instanceof ApiError ? e.message : "Неизвестная ошибка")
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
            <Palette className="w-5 h-5 text-slate-700" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Редизайн PPTX</h1>
        </div>
        <p className="text-slate-600 ml-12">
          Превращает сырую презентацию в оформленную по одному из трёх фирменных
          стилей.
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

        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-700">Стиль</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {STYLES.map((s) => {
              const active = style === s.id
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setStyle(s.id)}
                  disabled={busy}
                  aria-pressed={active}
                  className={cn(
                    "text-left rounded-lg border p-4 transition bg-white",
                    "hover:border-slate-400",
                    active
                      ? "border-slate-900 ring-2 ring-slate-900 ring-offset-2"
                      : "border-slate-200",
                    busy && "opacity-60 cursor-not-allowed",
                  )}
                >
                  <div className="flex gap-2 mb-3">
                    <div
                      className="w-8 h-8 rounded"
                      style={{ backgroundColor: s.colors[0] }}
                      aria-hidden
                    />
                    <div
                      className="w-8 h-8 rounded border border-slate-200"
                      style={{ backgroundColor: s.colors[1] }}
                      aria-hidden
                    />
                  </div>
                  <p className="font-medium text-slate-900">{s.name}</p>
                  <p className="text-xs text-slate-600 mt-1">{s.description}</p>
                  <p className="text-xs text-slate-400 mt-2">{s.font}</p>
                </button>
              )
            })}
          </div>
        </div>

        <ProcessingStatus
          status={status}
          progress={progress}
          message={status === "success" ? "Файл сохранён в Загрузки" : undefined}
          error={error}
        />

        <div className="flex gap-3">
          <Button onClick={handleSubmit} disabled={!file || busy}>
            {busy ? "Обработка..." : "Редизайн"}
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

