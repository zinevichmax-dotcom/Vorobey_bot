"use client"

import { useState, useEffect } from "react"
import { FileUpload } from "@/components/FileUpload"
import { ProcessingStatus, type Status } from "@/components/ProcessingStatus"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api, ApiError } from "@/lib/api"
import { FileText, Sparkles } from "lucide-react"

interface ContractMetadata {
  contract_name: string
  contract_number: string
  contract_date: string
  party_1: string
  party_2: string
}

export default function SupplementPage() {
  const [file, setFile] = useState<File | null>(null)
  const [contractName, setContractName] = useState("Договор")
  const [contractNumber, setContractNumber] = useState("")
  const [contractDate, setContractDate] = useState("")
  const [party1, setParty1] = useState("")
  const [party2, setParty2] = useState("")
  const [status, setStatus] = useState<Status>("idle")
  const [error, setError] = useState("")
  const [autofilling, setAutofilling] = useState(false)
  const [autofilled, setAutofilled] = useState(false)

  // Автоподсос метаданных после выбора файла
  useEffect(() => {
    if (!file) {
      setAutofilled(false)
      return
    }

    let cancelled = false

    async function extract() {
      setAutofilling(true)
      setAutofilled(false)

      try {
        const meta = await api.postFile<ContractMetadata>(
          "/extract/contract-metadata",
          file!,
        )

        if (cancelled) return

        if (meta.contract_name) setContractName(meta.contract_name)
        if (meta.contract_number) setContractNumber(meta.contract_number)
        if (meta.contract_date) setContractDate(meta.contract_date)
        if (meta.party_1) setParty1(meta.party_1)
        if (meta.party_2) setParty2(meta.party_2)

        setAutofilled(true)
      } catch {
        // тихо игнорируем — пользователь заполнит руками
      } finally {
        if (!cancelled) setAutofilling(false)
      }
    }

    extract()
    return () => {
      cancelled = true
    }
  }, [file])

  async function handleSubmit() {
    if (!file) return
    if (!party1.trim() || !party2.trim()) {
      setError("Укажите обе стороны")
      setStatus("error")
      return
    }

    setError("")
    setStatus("processing")

    try {
      const extraFields: Record<string, string> = {
        contract_name: contractName,
        party_1: party1,
        party_2: party2,
      }
      if (contractNumber.trim()) extraFields.contract_number = contractNumber
      if (contractDate.trim()) extraFields.contract_date = contractDate

      const blob = await api.postFile<Blob>("/generate/supplement", file, extraFields)

      const filename = `supplement_${file.name}`
      api.downloadBlob(blob, filename)
      setStatus("success")
    } catch (e) {
      setStatus("error")
      setError(e instanceof ApiError ? e.message : "Неизвестная ошибка")
    }
  }

  function handleReset() {
    setFile(null)
    setContractName("Договор")
    setContractNumber("")
    setContractDate("")
    setParty1("")
    setParty2("")
    setStatus("idle")
    setError("")
    setAutofilled(false)
  }

  const busy = status === "processing"
  const canSubmit = file && party1.trim() && party2.trim() && !busy

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-slate-100 rounded-md">
            <FileText className="w-5 h-5 text-slate-700" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Допсоглашение</h1>
        </div>
        <p className="text-slate-600 ml-12">
          Загрузите DOCX договора с Track Changes — получите дополнительное соглашение на основе
          правок.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg p-6 space-y-6">
        <div>
          <Label className="mb-2 block">Договор с правками (Track Changes)</Label>
          <FileUpload
            file={file}
            onFileSelect={setFile}
            accept=".docx"
            label="Выберите DOCX с правками в режиме рецензирования"
          />
          {autofilling && (
            <p className="text-sm text-slate-500 mt-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4 animate-pulse" />
              Распознаём данные договора...
            </p>
          )}
          {autofilled && !autofilling && (
            <p className="text-sm text-green-700 mt-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Поля заполнены автоматически — проверьте и откорректируйте при необходимости
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="contractName">Название договора</Label>
            <Input
              id="contractName"
              value={contractName}
              onChange={(e) => setContractName(e.target.value)}
              placeholder="Договор аренды"
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="contractNumber">Номер договора (опционально)</Label>
            <Input
              id="contractNumber"
              value={contractNumber}
              onChange={(e) => setContractNumber(e.target.value)}
              placeholder="123/2025"
              className="mt-2"
            />
          </div>

          <div className="md:col-span-2">
            <Label htmlFor="contractDate">Дата договора (опционально)</Label>
            <Input
              id="contractDate"
              value={contractDate}
              onChange={(e) => setContractDate(e.target.value)}
              placeholder="15.03.2025"
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="party1">Сторона 1 *</Label>
            <Input
              id="party1"
              value={party1}
              onChange={(e) => setParty1(e.target.value)}
              placeholder="ООО «Ромашка»"
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="party2">Сторона 2 *</Label>
            <Input
              id="party2"
              value={party2}
              onChange={(e) => setParty2(e.target.value)}
              placeholder="ИП Иванов И.И."
              className="mt-2"
            />
          </div>
        </div>

        <ProcessingStatus
          status={status}
          message={
            status === "processing"
              ? "Анализируем правки и формируем допсоглашение..."
              : status === "success"
                ? "Допсоглашение сохранено в Загрузки"
                : undefined
          }
          error={error}
        />

        <div className="flex gap-3">
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {busy ? "Генерация..." : "Сгенерировать допсоглашение"}
          </Button>

          {(status === "success" || status === "error") && (
            <Button variant="outline" onClick={handleReset}>
              Новый договор
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

