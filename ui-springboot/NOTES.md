# ui-springboot/ — thin Spring Boot + Thymeleaf dashboard (:8080)

**Deliberately not scaffolded yet.** It's generated from Spring Initializr when
JDK 17+ and Maven/Gradle are installed (see `SETUP.md` §4) — generating Java
stubs before the toolchain exists would just be dead weight. The Python core
(:8000) is the critical path; the UI bolts on once endpoints return real data.

## When you generate it
- Spring Initializr deps: **Spring Web**, **Thymeleaf** (Spring AI / Ollama-in-
  Java NOT needed — Ollama is driven from Python).
- Keep Maven cache off C:: `<localRepository>D:\m2-repo</localRepository>`.
- **Zero agent logic in Java.** One `@Controller`, one HTTP client calling the
  Python service, Thymeleaf templates.

## What the UI shows
- Lot list with flagged status (GET `/lots`).
- A flagged lot: drafted disposition + cited SOP rule + one parametric/die-map
  chart (GET `/lot/{id}`, `/disposition/{id}`).
- **Approve / Override** buttons that POST to the Python service.

## Learning goals (why Spring is here)
DI / IoC, `@Controller`, `application.yml` config, embedded Tomcat, Thymeleaf
templating, calling an HTTP service. See `PREP_KNOWLEDGE.md` §7.
