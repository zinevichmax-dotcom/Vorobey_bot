import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import bcrypt from "bcryptjs"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        username: { label: "Логин", type: "text" },
        password: { label: "Пароль", type: "password" },
      },
      async authorize(credentials) {
        const username = credentials?.username as string
        const password = credentials?.password as string

        if (!username || !password) return null

        const validUsername = process.env.AUTH_USERNAME
        const validPasswordHash = process.env.AUTH_PASSWORD_HASH

        if (!validUsername || !validPasswordHash) {
          console.error("AUTH_USERNAME или AUTH_PASSWORD_HASH не заданы")
          return null
        }

        if (username !== validUsername) return null

        const isValid = bcrypt.compareSync(password, validPasswordHash)
        if (!isValid) return null

        return { id: "1", name: username, email: `${username}@local` }
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  trustHost: true,
})

