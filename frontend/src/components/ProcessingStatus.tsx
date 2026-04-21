"use client"

import { Loader2, CheckCircle2, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export type Status = "idle" | "uploading" | "processing" | "success" | "error"

interface ProcessingStatusProps {
  status: Status
  progress?: number
  message?: string
  error?: string
}

export function ProcessingStatus({
  status,
  progress,
  message,
  error,
}: ProcessingStatusProps) {
  if (status === "idle") return null

  return (
    <div
      className={cn(
        "rounded-lg p-4 flex items-start gap-3",
        status === "error" && "bg-red-50 border border-red-200",
        status === "success" && "bg-green-50 border border-green-200",
        (status === "uploading" || status === "processing") &&
          "bg-slate-50 border border-slate-200",
      )}
    >
      {status === "error" && <XCircle className="w-5 h-5 text-red-600 mt-0.5" />}
      {status === "success" && (
        <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
      )}
      {(status === "uploading" || status === "processing") && (
        <Loader2 className="w-5 h-5 text-slate-600 animate-spin mt-0.5" />
      )}

      <div className="flex-1 min-w-0">
        {status === "uploading" && (
          <>
            <p className="text-sm font-medium text-slate-900">Загрузка файла...</p>
            {typeof progress === "number" && (
              <div className="mt-2 w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-slate-700 h-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
          </>
        )}

        {status === "processing" && (
          <>
            <p className="text-sm font-medium text-slate-900">Обработка...</p>
            {message && <p className="text-xs text-slate-600 mt-1">{message}</p>}
          </>
        )}

        {status === "success" && (
          <p className="text-sm font-medium text-green-900">{message || "Готово"}</p>
        )}

        {status === "error" && (
          <>
            <p className="text-sm font-medium text-red-900">Ошибка</p>
            <p className="text-xs text-red-700 mt-1">
              {error || "Неизвестная ошибка"}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

