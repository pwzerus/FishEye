import Link from "next/link";

import { LEGAL, type LegalText } from "@/lib/legal";

// Spanish translation of en.tsx, section for section. The English version
// is the one that applies. Change this with en.tsx.

function Body() {
  return (
    <>
      <section>
        <h2>Quiénes somos</h2>
        <p>
          FishEye ({LEGAL.site}) se gestiona{LEGAL.operator ? ` por ${LEGAL.operator}` : ""} desde los Estados Unidos.
          Envía tus preguntas sobre esta política o sobre tus datos a{" "}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>.
        </p>
      </section>

      <section>
        <h2>Qué recopilamos</h2>
        <p>
          Puedes usar el mapa, las guías de peces, Preguntar, la identificación por foto (unas pocas fotos al día) y los
          comentarios sin una cuenta. Lo que guardamos:
        </p>
        <ul>
          <li>
            <strong>Tu cuenta:</strong> tu correo electrónico y tu nombre visible, y tu contraseña, guardada solo como un
            hash scrypt que no podemos revertir. Si inicias sesión con Google, Google nos indica tu correo electrónico y
            un identificador de cuenta; nunca vemos tu contraseña de Google. Registramos cuándo te uniste y cuándo
            iniciaste sesión por última vez.
          </li>
          <li>
            <strong>Tus sesiones:</strong> una cookie contiene un token aleatorio (solo guardamos un hash de él), junto
            con la última vez que se usó la sesión y el nombre y la versión de tu navegador.
          </li>
          <li>
            <strong>Las capturas que compartes:</strong> dónde colocaste el marcador, su título, notas, peces, fecha y
            fotos. Volvemos a guardar cada foto y le quitamos los datos ocultos, incluidos la posición GPS y los datos de
            la cámara, antes de almacenarla.
          </li>
          <li>
            <strong>Denuncias y moderación:</strong> las denuncias que presentas sobre una captura o un comentario, y un
            registro de lo que hacen los moderadores.
          </li>
          <li>
            <strong>Respuestas de IA y Plus:</strong> cuántas respuestas de IA usas cada día, para que funcione el límite
            diario, y si tu cuenta tiene FishEye Plus y hasta cuándo. El conteo diario se guarda con un código
            irreversible generado a partir de tu correo electrónico, no con la dirección en sí.
          </li>
          <li>
            <strong>Me gusta y comentarios:</strong> qué capturas te gustaron y los comentarios que escribiste. Los
            comentarios y la cantidad de me gusta de una captura son públicos. Tu nombre también aparece en las
            clasificaciones por las capturas públicas que compartes, salvo que lo desactives en tu página de cuenta.
          </li>
          <li>
            <strong>Alertas de capturas, si las configuras:</strong> el pez, el lugar (redondeado a aproximadamente un
            kilómetro), la distancia y tu idioma, para poder enviarte correos. Cada correo incluye un enlace para darte de
            baja, y las alertas se eliminan junto con tu cuenta.
          </li>
          <li>
            <strong>Los comentarios que nos envías:</strong> tu mensaje, la página en la que estabas y tu idioma. Si
            iniciaste sesión, se guarda con tu cuenta para que podamos responderte; si eliminas tu cuenta, conservamos el
            mensaje sin indicar quién lo envió. Si no iniciaste sesión, se guarda sin cuenta, y con un correo electrónico
            solo si dejas uno para recibir respuesta.
          </li>
          <li>
            <strong>Preguntas que Preguntar no pudo responder:</strong> la pregunta, su idioma y el estado o el pez que
            elegiste, para saber qué guías escribir después. No registramos quién preguntó, primero quitamos correos
            electrónicos, números de teléfono y enlaces, y las eliminamos después de 90 días.
          </li>
          <li>
            <strong>Conteo de visitas:</strong> cuántas veces se abrió cada página cada día, y el sitio web donde estaba
            un enlace a nosotros (solo su nombre, como reddit.com) o una etiqueta en el enlace (como ?ref=reddit). Nada
            más: ninguna dirección IP, ninguna cookie ni otro identificador, nada que distinga a un visitante de otro o
            que siga a alguien entre páginas. Lo usamos para saber si alguien encuentra FishEye, y desde dónde.
          </li>
          <li>
            <strong>Registros del servidor:</strong> como la mayoría de los sitios web, nuestro servidor registra cada
            solicitud (dirección IP, página, hora, navegador) para mantener el sitio en funcionamiento y seguro. Los
            conservamos solo el tiempo necesario para ello. Para frenar el abuso, el servidor también cuenta las
            solicitudes por dirección IP en su memoria (por ejemplo, las identificaciones por foto gratuitas al día sin
            cuenta); esos conteos no se guardan y desaparecen en menos de un día.
          </li>
        </ul>
      </section>

      <section>
        <h2>Tus lugares de pesca</h2>
        <p>
          Una captura que mantienes <strong>privada</strong> la ves tú y, cuando una denuncia o un problema lo requiere,
          nuestros moderadores. Una captura <strong>pública</strong> la ve todo el mundo, pero de forma predeterminada
          solo en su lago (o, lejos de los lagos, en su condado): el lugar exacto queda entre tú y los moderadores, salvo
          que elijas mostrar a otros pescadores “El lugar exacto”. Puedes cambiarlo, o hacer privada una captura, en
          cualquier momento.
        </p>
      </section>

      <section>
        <h2>Qué hacemos con ello</h2>
        <ul>
          <li>Gestionar tu cuenta y mostrarte tus capturas y, si las hiciste públicas, mostrárselas a otros.</li>
          <li>
            Identificar un pez o un equipo de pesca a partir de una foto, y comprobar que la foto de una captura muestra
            el pez que indicaste. Esto se hace en nuestro propio servidor, y una foto revisada por sí sola no se guarda.
            Una foto solo se envía a otra empresa si le preguntas a la IA sobre ella (consulta Anthropic más abajo).
          </li>
          <li>
            Mantener FishEye seguro: limitar el spam y el abuso, atender las denuncias y mantener el servicio en
            funcionamiento.
          </li>
          <li>Responderte cuando nos escribes.</li>
        </ul>
        <p>
          No vendemos ni alquilamos información personal, no la compartimos con fines publicitarios, y FishEye no tiene
          anuncios, ni cookies de rastreo, ni servicios de análisis externos. El conteo de visitas mencionado arriba es
          nuestro y no dice nada sobre quién visitó.
        </p>
      </section>

      <section>
        <h2>Quién más la maneja</h2>
        <ul>
          <li>
            <strong>Amazon Web Services</strong> aloja los servidores y la base de datos de FishEye, en los Estados
            Unidos.
          </li>
          <li>
            <strong>Anthropic</strong>, cuando le preguntas a la IA en Preguntar: tu pregunta y los pasajes de las guías
            que coinciden con ella, o la foto sobre la que preguntas, se envían al modelo de IA de Anthropic para escribir
            la respuesta. Primero volvemos a guardar la foto sin su ubicación ni los datos de la cámara, y no la
            conservamos. Los datos de tu cuenta no se envían. No incluyas información personal en una pregunta ni en una
            foto.
          </li>
          <li>
            <strong>Google</strong>, solo si usas “Iniciar sesión con Google”.
          </li>
          <li>
            <strong>Nominatim de OpenStreetMap</strong> recibe el texto del lugar que buscas, desde nuestro servidor, no
            desde tu navegador.
          </li>
          <li>
            Tu navegador carga directamente <strong>los mosaicos del mapa de MapTiler</strong> (y de OpenStreetMap, si
            MapTiler no está disponible) y <strong>las fotos de peces de Wikimedia Commons</strong>. Como cualquier sitio
            web, reciben tu dirección IP y los datos de tu navegador; se aplican sus propias políticas de privacidad.
          </li>
          <li>Las autoridades, si la ley lo exige, o para proteger la seguridad de alguien.</li>
        </ul>
        <p>
          Cuando usas “Cerca de mí”, la ubicación de tu dispositivo se usa en tu navegador; para abrir las capturas
          cercanas, buscamos tu condado en nuestro servidor y no guardamos ni registramos la posición.
        </p>
      </section>

      <section>
        <h2>Cookies y almacenamiento del navegador</h2>
        <p>
          Una cookie mantiene tu sesión iniciada. Tu navegador también guarda algunas preferencias, como el estado que
          elegiste para las normas de pesca. El conteo de visitas no usa cookies ni guarda nada en tu navegador. Nada se
          usa para publicidad ni rastreo.
        </p>
      </section>

      <section>
        <h2>Tus opciones</h2>
        <ul>
          <li>Editar o eliminar cualquier captura, hacerla privada o cambiar quién ve su lugar exacto.</li>
          <li>
            Eliminar tu cuenta desde tu <Link href="/account">página de cuenta</Link>. Eso elimina tu cuenta, tus
            sesiones y tus capturas con sus fotos. Las denuncias que presentaste se conservan, sin tu nombre, para que un
            moderador pueda terminar de revisarlas. El conteo de respuestas de IA que usaste se conserva hasta 30 días con
            su código irreversible, de modo que eliminar una cuenta y crearla de nuevo no restablece las respuestas
            gratuitas.
          </li>
          <li>
            Pedirnos una copia de tus datos, o que los corrijamos o eliminemos, en{" "}
            <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>. Respondemos en un plazo de 30 días.
          </li>
        </ul>
      </section>

      <section>
        <h2>Cuánto tiempo la conservamos</h2>
        <p>
          Hasta que la eliminas o eliminas tu cuenta. Los conteos diarios de respuestas de IA se eliminan después de 30
          días. Las copias de seguridad de la base de datos pueden conservar una copia por poco tiempo antes de ser
          reemplazadas.
        </p>
      </section>

      <section>
        <h2>Seguridad</h2>
        <p>
          El sitio usa HTTPS, las contraseñas y los tokens de sesión se guardan solo como hashes, y solo los
          administradores de FishEye pueden acceder a los servidores. Ningún sistema es perfectamente seguro; si ocurre
          algo que te afecte, te lo diremos.
        </p>
      </section>

      <section>
        <h2>Menores</h2>
        <p>
          Las cuentas de FishEye son para personas de {LEGAL.minimumAge} años o más, y cualquier menor de 18 años
          necesita el permiso de su madre, padre o tutor. Cualquier persona puede consultar el mapa y las guías sin una
          cuenta. De acuerdo con la Ley de Protección de la Privacidad Infantil en Línea (COPPA), no recopilamos a
          sabiendas información personal de menores de {LEGAL.minimumAge} años. Si nos enteramos de que un menor de{" "}
          {LEGAL.minimumAge} años creó una cuenta, la eliminamos; su madre, padre o tutor puede pedírnoslo en{" "}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>.
        </p>
      </section>

      <section>
        <h2>Cambios</h2>
        <p>
          Cuando cambiamos esta política, actualizamos la fecha que aparece arriba y, si se trata de un cambio
          importante, lo indicamos en el sitio antes de que se aplique.
        </p>
      </section>
    </>
  );
}

export const es: LegalText = {
  title: "Política de privacidad",
  lede: "FishEye recopila lo que necesita para gestionar tu cuenta y mostrar tus capturas. No vendemos tus datos, no mostramos anuncios y nunca revelamos tus lugares de pesca.",
  description: "Qué recopila FishEye, por qué, quién más la ve y cómo eliminarla.",
  Body,
};
