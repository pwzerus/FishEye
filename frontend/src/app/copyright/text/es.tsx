import Link from "next/link";

import { LEGAL, type LegalText } from "@/lib/legal";

import { NOTICE_SUBJECT, noticeHref } from "./en";

// Spanish translation of en.tsx, section for section. The English version
// is the one that applies. Change this with en.tsx.

function Body() {
  return (
    <>
      <section>
        <h2>Una captura que incumple las normas</h2>
        <p>
          Abre la captura y usa <strong>Reportar</strong>. Elige el motivo (spam, una foto inapropiada, una ubicación
          incorrecta, propiedad privada, algo peligroso o ilegal) y añade una nota. Una captura que denuncian varias
          personas se oculta hasta que un moderador la revisa. Necesitas una cuenta para denunciar, de modo que una sola
          persona no puede ocultar una captura por su cuenta.
        </p>
        <p>
          Para otros casos, como tu información personal publicada por otra persona o una captura que lleva a la gente a
          tu terreno, escribe a <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a> con el enlace.
        </p>
      </section>

      <section>
        <h2>Avisos de derechos de autor</h2>
        <p>
          Si algo en FishEye usa tu obra protegida por derechos de autor sin permiso, envía un aviso a{" "}
          <a href={noticeHref}>{LEGAL.contactEmail}</a> con el asunto “{NOTICE_SUBJECT}” (aviso de derechos de autor)
          que incluya:
        </p>
        <ol>
          <li>la obra que, según tú, se infringe;</li>
          <li>el enlace a la captura o la página de FishEye que la usa;</li>
          <li>tu nombre, dirección postal, número de teléfono y correo electrónico;</li>
          <li>
            una declaración de que crees de buena fe que el uso no está autorizado por ti, tu representante o la ley;
          </li>
          <li>
            una declaración de que la información de tu aviso es exacta y, bajo pena de perjurio, de que eres el titular
            de los derechos de autor o puedes actuar en su nombre;
          </li>
          <li>tu firma física o electrónica (basta con escribir tu nombre completo).</li>
        </ol>
        <p>
          Retiramos el contenido, informamos a quien lo publicó y le damos una copia del aviso. Quien presente a sabiendas
          reclamaciones falsas puede ser responsable de los daños.
        </p>
      </section>

      <section>
        <h2>Si retiraron tu captura</h2>
        <p>
          Si crees que se eliminó por error, o tienes derecho a publicarla, envía un contraaviso a la misma dirección con:
          el enlace a lo que se eliminó; una declaración, bajo pena de perjurio, de que crees de buena fe que se eliminó
          por error o por una identificación equivocada; tu nombre, dirección y número de teléfono; tu consentimiento a la
          jurisdicción del tribunal federal que corresponde a tu dirección (o, fuera de EE. UU., de cualquier tribunal
          donde se pueda encontrar a FishEye) y a recibir notificaciones de la persona que envió el aviso; y tu firma.
          Salvo que la persona que presentó la queja nos informe en un plazo de 10 días hábiles de que acudió a los
          tribunales, podemos restablecer el contenido.
        </p>
      </section>

      <section>
        <h2>Infractores reincidentes</h2>
        <p>
          Cerramos las cuentas de quienes publican repetidamente contenido que infringe los derechos de autor de otras
          personas. Consulta también los <Link href="/terms">términos de uso</Link>.
        </p>
      </section>
    </>
  );
}

export const es: LegalText = {
  title: "Derechos de autor y contenido",
  lede: "Cómo avisarnos de una captura que incumple las normas, o de una foto o un texto publicados sin el permiso de su dueño.",
  description: "Cómo denunciar una captura que incumple las normas, o contenido que infringe tus derechos de autor.",
  Body,
};
