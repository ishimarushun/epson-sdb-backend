export function LandingPage({ title, body }: { title: string; body: string }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-5 py-12">
      <p className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-moss">Event print</p>
      <h1 className="text-4xl font-semibold text-ink sm:text-5xl">{title}</h1>
      <p className="mt-5 text-lg leading-8 text-ink/75">{body}</p>
    </main>
  );
}
