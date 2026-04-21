"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { signOut } from "next-auth/react"
import { cn } from "@/lib/utils"
import {
  Home,
  Wand2,
  FileText,
  GitCompare,
  ShieldCheck,
  Users,
  LogOut,
} from "lucide-react"

const modules = [
  { href: "/", label: "Главная", icon: Home },
  { href: "/normalize", label: "Нормализация PPTX", icon: Wand2 },
  { href: "/supplement", label: "Допсоглашение", icon: FileText },
  { href: "/compare", label: "Сравнение документов", icon: GitCompare },
  { href: "/compliance", label: "Compliance проверка", icon: ShieldCheck },
  { href: "/interest", label: "Заинтересованность", icon: Users },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-xl font-bold">Vorobey Bot</h1>
        <p className="text-xs text-slate-400 mt-1">Рабочий кабинет</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {modules.map(({ href, label, icon: Icon }) => {
          const active =
            pathname === href || (href !== "/" && pathname.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition",
                active
                  ? "bg-slate-800 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white",
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition"
        >
          <LogOut className="w-4 h-4" />
          Выйти
        </button>
      </div>
    </aside>
  )
}

