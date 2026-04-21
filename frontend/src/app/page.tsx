import { auth, signOut } from "@/lib/auth"
import { Button } from "@/components/ui/button"

export default async function HomePage() {
  const session = await auth()

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Vorobey Bot</h1>
            <p className="text-slate-600 mt-1">
              Добро пожаловать, {session?.user?.name}
            </p>
          </div>
          <form
            action={async () => {
              "use server"
              await signOut({ redirectTo: "/login" })
            }}
          >
            <Button type="submit" variant="outline">
              Выйти
            </Button>
          </form>
        </div>

        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Модули</h2>
          <p className="text-slate-500">
            Модули будут подключены на следующих фазах.
          </p>
        </div>
      </div>
    </div>
  )
}
