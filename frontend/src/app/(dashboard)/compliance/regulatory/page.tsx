"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { FileUpload } from "@/components/FileUpload"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api, ApiError } from "@/lib/api"
import { ArrowLeft, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"

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
}

const DOC_TYPES = [
  {
    key: "fz_208",
    label: "ФЗ-208 «Об акционерных обществах»",
    hint: "Загрузите актуальную редакцию в .docx или .odt",
    defaultName: "ФЗ-208 «Об акционерных обществах»",
  },
  {
    key: "fz_14",
    label: "ФЗ-14 «Об обществах с ограниченной ответственностью»",
    hint: "Загрузите актуальную редакцию в .docx или .odt",
    defaultName: "ФЗ-14 «Об ООО»",
  },
  {
    key: "charter",
    label: "Устав общества",
    hint: "Устав вашей компании",
    defaultName: "Устав",
  },
  {
    key: "corporate_agreement",
    label: "Корпоративный договор",
    hint: "Акционерное соглашение или корпоративный договор",
    defaultName: "Корпоративный договор",
  },
]

export default function RegulatoryPage() {
  const [docs, setDocs] = useState<RegulatoryDoc[]>([])
  const [loading, setLoading] = useState(true)

  async function loadDocs() {
    try {
      const res = await api.get<RegulatoryList>("/compliance/regulatory-docs")
      setDocs(res.documents || [])
    } catch {
      setDocs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDocs()
  }, [])

  return (
    <div>
      <div className="mb-8">
        <Link
          href="/compliance"
          className="inline-flex items-center text-sm text-slate-600 hover:text-slate-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          К Compliance проверке
        </Link>
        <h1 className="text-3xl font-bold text-slate-900">Управление НПА</h1>
        <p className="text-slate-600 mt-1">
          Загрузите 4 документа один раз — они будут использоваться при каждой проверке.
        </p>
      </div>

      <div className="space-y-4">
        {DOC_TYPES.map((type) => {
          const existing = docs.find((d) => d.doc_type === type.key)
          return (
            <DocumentSlot
              key={type.key}
              type={type}
              existing={existing}
              loading={loading}
              onChange={loadDocs}
            />
          )
        })}
      </div>
    </div>
  )
}

interface DocumentSlotProps {
  type: (typeof DOC_TYPES)[number]
  existing?: RegulatoryDoc
  loading: boolean
  onChange: () => void
}

function DocumentSlot({ type, existing, loading, onChange }: DocumentSlotProps) {
  const [file, setFile] = useState<File | null>(null)
  const [docName, setDocName] = useState(type.defaultName)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)

  async function handleUpload() {
    if (!file) return
    setError("")
    setSuccess(false)
    setUploading(true)

    try {
      await api.postFile<unknown>("/compliance/upload-regulatory", file, {
        doc_type: type.key,
        doc_name: docName,
      })
      setSuccess(true)
      setFile(null)
      onChange()
      setTimeout(() => setSuccess(false), 3000)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Неизвестная ошибка")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-3">
          {loading ? (
            <Loader2 className="w-5 h-5 text-slate-400 animate-spin mt-0.5" />
          ) : existing ? (
            <CheckCircle2 className="w-5 h-5 text-green-600 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-slate-400 mt-0.5" />
          )}
          <div>
            <h3 className="font-semibold text-slate-900">{type.label}</h3>
            <p className="text-sm text-slate-500 mt-1">{type.hint}</p>
          </div>
        </div>
        {existing && (
          <span className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded">
            Загружено
          </span>
        )}
      </div>

      {existing && (
        <div className="bg-slate-50 border border-slate-200 rounded-md p-3 mb-4 text-sm">
          <div className="font-medium text-slate-900">{existing.doc_name}</div>
          <div className="text-xs text-slate-500 mt-1">
            {existing.paragraphs} абзацев · {existing.char_count.toLocaleString("ru")} символов
            {existing.approx_tokens &&
              ` · ~${existing.approx_tokens.toLocaleString("ru")} токенов`}
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <Label htmlFor={`name-${type.key}`}>Название документа</Label>
          <Input
            id={`name-${type.key}`}
            value={docName}
            onChange={(e) => setDocName(e.target.value)}
            className="mt-2"
          />
        </div>

        <FileUpload
          file={file}
          onFileSelect={setFile}
          accept=".docx,.odt"
          label={existing ? "Загрузить новую версию" : "Выберите файл"}
        />

        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
            {error}
          </div>
        )}

        {success && (
          <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded p-3">
            Документ загружен
          </div>
        )}

        <Button onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? "Загрузка..." : existing ? "Заменить документ" : "Загрузить"}
        </Button>
      </div>
    </div>
  )
}

