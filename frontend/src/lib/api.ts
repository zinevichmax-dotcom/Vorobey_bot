/**
 * Обёртка над backend API.
 * Все запросы идут через эти функции.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = "ApiError"
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Ошибка ${response.status}`
    try {
      const data = await response.json()
      message = data.detail || data.message || message
    } catch {
      // если ответ не JSON — оставляем базовое сообщение
    }
    throw new ApiError(response.status, message)
  }

  const contentType = response.headers.get("content-type") || ""
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>
  }
  // Для файлов — возвращаем blob
  return response.blob() as unknown as T
}

export const api = {
  /**
   * GET запрос, возвращает JSON.
   */
  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
    })
    return handleResponse<T>(response)
  },

  /**
   * POST с JSON телом.
   */
  async postJson<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    })
    return handleResponse<T>(response)
  },

  /**
   * POST с файлом (multipart).
   * Возвращает blob (для скачивания) или JSON (если format=json).
   */
  async postFile<T>(
    path: string,
    file: File,
    extraFields?: Record<string, string>,
    onProgress?: (percent: number) => void,
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const formData = new FormData()
      formData.append("file", file)
      if (extraFields) {
        for (const [key, value] of Object.entries(extraFields)) {
          formData.append(key, value)
        }
      }

      const xhr = new XMLHttpRequest()
      xhr.open("POST", `${API_URL}${path}`)

      if (onProgress) {
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            onProgress(Math.round((e.loaded / e.total) * 100))
          }
        })
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const contentType = xhr.getResponseHeader("content-type") || ""
          if (contentType.includes("application/json")) {
            resolve(JSON.parse(xhr.responseText))
          } else {
            resolve(xhr.response as T)
          }
        } else {
          let message = `Ошибка ${xhr.status}`
          try {
            const data = JSON.parse(xhr.responseText)
            message = data.detail || message
          } catch {
            /* noop */
          }
          reject(new ApiError(xhr.status, message))
        }
      }

      xhr.onerror = () => reject(new ApiError(0, "Сеть недоступна"))
      xhr.responseType = "blob"
      xhr.send(formData)
    })
  },

  /**
   * POST с двумя файлами (для /compare/docx).
   */
  async postTwoFiles<T>(
    path: string,
    fileA: File,
    fileB: File,
    extraFields?: Record<string, string>,
  ): Promise<T> {
    const formData = new FormData()
    formData.append("file_a", fileA)
    formData.append("file_b", fileB)
    if (extraFields) {
      for (const [key, value] of Object.entries(extraFields)) {
        formData.append(key, value)
      }
    }

    const response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      body: formData,
    })
    return handleResponse<T>(response)
  },

  /**
   * Скачать blob как файл.
   */
  downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  },
}

