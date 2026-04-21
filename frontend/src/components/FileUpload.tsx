"use client"

import { useState, useRef, DragEvent } from "react"
import { Upload, FileText, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface FileUploadProps {
  onFileSelect: (file: File | null) => void
  accept?: string
  maxSizeMb?: number
  label?: string
  file?: File | null
}

export function FileUpload({
  onFileSelect,
  accept = ".docx,.pptx,.odt",
  maxSizeMb = 50,
  label = "Перетащите файл или нажмите для выбора",
  file,
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  function validateAndSet(selected: File | null) {
    setError("")
    if (!selected) {
      onFileSelect(null)
      return
    }

    // Проверка размера
    if (selected.size > maxSizeMb * 1024 * 1024) {
      setError(`Файл больше ${maxSizeMb} МБ`)
      return
    }

    // Проверка расширения
    const ext = "." + selected.name.split(".").pop()?.toLowerCase()
    const allowedExts = accept.split(",").map((e) => e.trim().toLowerCase())
    if (!allowedExts.includes(ext)) {
      setError(`Разрешены только: ${accept}`)
      return
    }

    onFileSelect(selected)
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    validateAndSet(dropped || null)
  }

  function handleClear(e: React.MouseEvent) {
    e.stopPropagation()
    if (inputRef.current) inputRef.current.value = ""
    onFileSelect(null)
    setError("")
  }

  return (
    <div className="space-y-2">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={cn(
          "relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition",
          dragOver
            ? "border-slate-600 bg-slate-50"
            : "border-slate-300 hover:border-slate-400",
          error && "border-red-400",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => validateAndSet(e.target.files?.[0] || null)}
        />

        {file ? (
          <div className="flex items-center justify-center gap-3">
            <FileText className="w-5 h-5 text-slate-500" />
            <span className="text-sm font-medium">{file.name}</span>
            <span className="text-xs text-slate-500">
              ({(file.size / 1024 / 1024).toFixed(2)} МБ)
            </span>
            <button
              onClick={handleClear}
              className="text-slate-400 hover:text-slate-700"
              type="button"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="w-8 h-8 text-slate-400" />
            <p className="text-sm text-slate-600">{label}</p>
            <p className="text-xs text-slate-400">
              {accept} · до {maxSizeMb} МБ
            </p>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}

