"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { FileUpload } from "@/components/FileUpload"
import { ProcessingStatus, type Status } from "@/components/ProcessingStatus"
import { Button } from "@/components/ui/button"
import { api, ApiError } from "@/lib/api"
import { ShieldCheck, Settings, AlertCircle } from "lucide-react"

interface RegulatoryDoc {
  doc_type: string
  doc_name: string
  doc_type_label?: string
  paragraphs: number
  char_count: number
  approx_tokens?: number
}

interface RegulatoryList {
  documents: RegulatoryDoc[]
  token_budget?: {
    passes: Record<string, { total_tokens: number; fits_200k: boolean }>
    total: number
  }
}

const REQUIRED_DOCS = [
  { key: "fz_208", label: "ФЗ-208 «Об АО»" },
  { key: "fz_14", label: "ФЗ-14 «Об ООО»" },
  { key: "charter", label: "Устав" },
  { key: "corporate_agreement", label: "Корпоративный договор" },
]

export default function CompliancePage() {
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<Status>("idle")
  const [error, setError] = useState("")
  const [regulatory, setRegulatory] = useState<RegulatoryDoc[]>([])
  const [loadingRegulatory, setLoadingRegulatory] = useState(true)

  useEffect(() => {
    loadRegulatory()
  }, [])

  async function loadRegulatory() {
    try {
      const res = await api.get<RegulatoryList>("/compliance/regulatory-docs")
      setRegulatory(res.documents || [])
    } catch {
      setRegulatory([])
    } finally {
      setLoadingRegulatory(false)
    }
  }

  async function handleSubmit() {
    if (!file) return
    setError("")
    setStatus("processing")

    try {
      const blob = await api.postFile<Blob>("/compliance/check", file)
      api.downloadBlob(blob, `compliance_${file.name}.docx`)
      setStatus("success")
    } catch (e) {
      setStatus("error")
      setError(e instanceof ApiError ? e.message : "Неизвестная ошибка")
    }
  }

  function handleReset() {
    setFile(null)
    setStatus("idle")
    setError("")
  }

  const uploadedTypes = new Set(regulatory.map((d) => d.doc_type))
  const missingDocs = REQUIRED_DOCS.filter((d) => !uploadedTypes.has(d.key))
  const allUploaded = missingDocs.length === 0
  const busy = status === "processing"

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-slate-100 rounded-md">
            <ShieldCheck className="w-5 h-5 text-slate-700" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Compliance проверка</h1>
        </div>
        <p className="text-slate-600 ml-12">
          Проверка документа на соответствие ФЗ-208, ФЗ-14, Уставу и Корпоративному договору. 3
          прохода, полные тексты.
        </p>
      </div>

      {/* Блок статуса НПА */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-semibold text-slate-900">Нормативная база</h2>
            <p className="text-sm text-slate-600 mt-1">
              {loadingRegulatory
                ? "Загрузка..."
                : allUploaded
                  ? "Все 4 документа загружены"
                  : `Загружено ${regulatory.length} из 4 документов`}
            </p>
          </div>
          <Link href="/compliance/regulatory">
            <Button variant="outline" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Управление НПА
            </Button>
          </Link>
        </div>

        {!loadingRegulatory && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {REQUIRED_DOCS.map(({ key, label }) => {
              const uploaded = uploadedTypes.has(key)
              return (
                <div
                  key={key}
                  className={`flex items-center gap-2 text-sm p-2 rounded ${
                    uploaded ? "text-green-700 bg-green-50" : "text-slate-500 bg-slate-50"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      uploaded ? "bg-green-500" : "bg-slate-300"
                    }`}
                  />
                  {label}
                  {uploaded && <span className="ml-auto text-xs">✓</span>}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Блок проверки */}
      <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
        {!allUploaded && !loadingRegulatory && (
          <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-md">
            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-900">
                Сначала загрузите все 4 нормативных документа
              </p>
              <p className="text-xs text-amber-700 mt-1">
                Проверка выполняется в 3 прохода и требует наличия всех НПА.{" "}
                <Link href="/compliance/regulatory" className="underline font-medium">
                  Перейти к загрузке
                </Link>
              </p>
            </div>
          </div>
        )}

        <div>
          <label className="text-sm font-medium text-slate-700 mb-2 block">
            Проверяемый документ (DOCX или ODT)
          </label>
          <FileUpload
            file={file}
            onFileSelect={setFile}
            accept=".docx,.odt"
            label="Выберите документ для проверки"
          />
        </div>

        <ProcessingStatus
          status={status}
          message={
            status === "processing"
              ? "Проверка по 3 проходам: ФЗ-208 → ФЗ-14 + Устав → Корп. договор. Это займёт 30-60 секунд..."
              : status === "success"
                ? "Справка о проверке сохранена в Загрузки"
                : undefined
          }
          error={error}
        />

        <div className="flex gap-3">
          <Button onClick={handleSubmit} disabled={!file || !allUploaded || busy}>
            {busy ? "Проверка..." : "Проверить документ"}
          </Button>

          {(status === "success" || status === "error") && (
            <Button variant="outline" onClick={handleReset}>
              Новая проверка
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

