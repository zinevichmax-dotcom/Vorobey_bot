import { auth } from "@/lib/auth"
import Link from "next/link"
import { Wand2, FileText, GitCompare, ShieldCheck, Users } from "lucide-react"

const modules = [
  {
    href: "/normalize",
    title: "Нормализация PPTX",
    description: "Унификация шрифтов, размеров и цветов в презентации",
    icon: Wand2,
  },
  {
    href: "/supplement",
    title: "Допсоглашение",
    description: "Генерация допсоглашения из Track Changes",
    icon: FileText,
  },
  {
    href: "/compare",
    title: "Сравнение документов",
    description: "Поиск различий между двумя версиями DOCX",
    icon: GitCompare,
  },
  {
    href: "/compliance",
    title: "Compliance проверка",
    description: "Проверка документа на соответствие ФЗ и уставу",
    icon: ShieldCheck,
  },
  {
    href: "/interest",
    title: "Заинтересованность",
    description: "Проверка сделки на заинтересованность по ЕГРЮЛ",
    icon: Users,
  },
]

export default async function HomePage() {
  const session = await auth()

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Добрый день</h1>
        <p className="text-slate-600 mt-1">
          {session?.user?.name}, выберите модуль для работы
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {modules.map(({ href, title, description, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="bg-white border border-slate-200 rounded-lg p-6 hover:border-slate-400 hover:shadow-sm transition"
          >
            <div className="flex items-start gap-4">
              <div className="p-2 bg-slate-100 rounded-md">
                <Icon className="w-5 h-5 text-slate-700" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900">{title}</h3>
                <p className="text-sm text-slate-600 mt-1">{description}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

