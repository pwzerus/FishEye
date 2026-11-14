import Link from "next/link";

import { LEGAL, legalDate } from "@/lib/legal";

import { Contents, Heading, sec, type SectionTitles, type TermsText } from "./shared";

// Spanish translation of en.tsx, section for section. The English version
// is the one that applies (General). Change this with en.tsx.

const TITLES: SectionTitles = {
  agreeing: "Aceptación de estos términos",
  accounts: "Quién puede usar FishEye",
  information: "La información de pesca es una guía, no la ley",
  "ai-answers": "Respuestas de IA",
  plus: "FishEye Plus",
  "your-content": "Lo que compartes",
  rules: "Normas de uso de FishEye",
  moderation: "Moderación y cierre de cuentas",
  "our-content": "Contenido propio de FishEye",
  "third-parties": "Datos, servicios y enlaces de terceros",
  copyright: "Reclamaciones de derechos de autor",
  safety: "Tu seguridad es responsabilidad tuya",
  disclaimers: "Sin garantías",
  liability: "Límites de nuestra responsabilidad",
  release: "Renuncia a reclamaciones",
  indemnity: "Reclamaciones causadas por ti",
  disputes: "Disputas y arbitraje",
  changes: "Cambios",
  "app-stores": "Apps de la App Store o Google Play",
  general: "Disposiciones generales",
  contact: "Contacto",
};

const day = (iso: string) => legalDate(iso, "es-US");

function Body() {
  const optOut = LEGAL.optOutDays;
  return (
    <>
      <section className="legal-summary" aria-labelledby="short-version">
        <h2 id="short-version">En resumen</h2>
        <ul>
          <li>
            <strong>FishEye es una guía.</strong> Las normas, el acceso, los datos de peces, los pronósticos y las
            respuestas de IA pueden estar equivocados. Lo que cuenta son las normas vigentes de tu estado y los letreros
            junto al agua.
          </li>
          <li>
            <strong>Pescar tiene riesgos.</strong> Tú decides dónde, cuándo y cómo pescar, y asumes ese riesgo.
          </li>
          <li>
            <strong>Las respuestas de IA vienen de una IA, no de una persona.</strong> Pueden equivocarse. Verifica todo
            lo que sea importante.
          </li>
          <li>
            <strong>Lo que publicas es tuyo.</strong> Permites que FishEye lo muestre, y eres responsable de ello.
          </li>
          <li>
            <strong>FishEye Plus se renueva hasta que lo canceles</strong>, y puedes cancelarlo en cualquier momento.
          </li>
          <li>
            <strong>Las disputas se resuelven mediante arbitraje individual o en un tribunal de reclamos menores</strong>,
            no mediante demandas colectivas, salvo que te excluyas en un plazo de {optOut} días.
          </li>
        </ul>
        <p className="legal-note">
          Este resumen te ayuda a orientarte. Lo que se aplica son los términos completos que aparecen a continuación.
        </p>
      </section>

      <Contents label="Contenido" titles={TITLES} />

      <section id="agreeing">
        <Heading id="agreeing" titles={TITLES} />
        <p>
          Estos términos de uso (“términos”) son un acuerdo entre tú y {LEGAL.operator || "el operador de FishEye"}{" "}
          (“FishEye”, “nosotros”). Abarcan el sitio web {LEGAL.site}, la app de FishEye y todo lo que contienen,
          incluidos el mapa, las guías de peces, Preguntar y sus respuestas de IA, la identificación por foto, las
          capturas, los comentarios y las cuentas (en conjunto, “FishEye”). Nuestra{" "}
          <Link href="/privacy">política de privacidad</Link> y nuestra{" "}
          <Link href="/copyright">página de derechos de autor</Link> forman parte de estos términos.
        </p>
        <p>
          Aceptas estos términos al crear una cuenta, obtener FishEye Plus o usar FishEye. Si no estás de acuerdo, no
          uses FishEye. Si tenías una cuenta antes del {day(LEGAL.updatedIso)}, estos términos se aplican a ti desde el{" "}
          {day(LEGAL.existingUsersFromIso)}; hasta entonces, se aplican los términos anteriores. Si usas FishEye en
          nombre de una organización, también aceptas estos términos en su nombre y confirmas que tienes autorización
          para hacerlo.
        </p>
        <p className="legal-conspicuous">
          Lee la sección {sec("disputes")}. En ella se establece que las disputas entre tú y FishEye se resuelven
          mediante arbitraje individual vinculante o en un tribunal de reclamos menores, sin demandas colectivas y sin
          jurado, salvo que te excluyas en un plazo de {optOut} días desde que aceptes estos términos por primera vez.
        </p>
      </section>

      <section id="accounts">
        <Heading id="accounts" titles={TITLES} />
        <ul>
          <li>
            Cualquier persona puede consultar el mapa y las guías. Para tener una cuenta debes tener {LEGAL.minimumAge}{" "}
            años o más. Nadie menor de {LEGAL.minimumAge} años puede crear una.
          </li>
          <li>
            Si tienes menos de 18 años, o no has alcanzado la mayoría de edad donde vives, necesitas el permiso de tu
            madre, padre o tutor. Al darlo, tu madre, padre o tutor acepta estos términos en tu nombre y es responsable
            de tu uso de FishEye, incluida cualquier compra.
          </li>
          <li>
            Proporciona información verdadera y mantenla actualizada. Una cuenta por persona: no crees cuentas
            adicionales, por ejemplo, para obtener más respuestas de IA o revisiones de fotos gratuitas.
          </li>
          <li>
            No compartas tu contraseña. Eres responsable de lo que ocurra en tu cuenta. Avísanos de inmediato si crees
            que otra persona la está usando.
          </li>
          <li>
            Confirmas que no figuras en ninguna lista del gobierno de EE. UU. de personas prohibidas o restringidas, y
            que no te encuentras en un país sujeto a embargo de EE. UU. o designado por EE. UU. como patrocinador del
            terrorismo.
          </li>
          <li>
            FishEye está hecho para pescar en los Estados Unidos. Si lo usas en otro lugar, lo haces por iniciativa
            propia y debes cumplir las leyes del lugar donde te encuentres.
          </li>
        </ul>
      </section>

      <section id="information">
        <Heading id="information" titles={TITLES} />
        <p>
          FishEye reúne datos públicos, sus propias guías, capturas de otros pescadores y estimaciones por computadora.
          Trabajamos para que sea correcto, pero no podemos garantizar que sea exacto, completo, actual o adecuado para
          tu cuerpo de agua. Úsalo para planificar y luego verifica.
        </p>
        <ul>
          <li>
            <strong>Normas y licencias.</strong> Las licencias de pesca, las temporadas, los límites de tamaño y de
            captura, las normas sobre carnada y los cierres cambian, y varían según el estado y el cuerpo de agua. Los
            resúmenes de FishEye pueden estar desactualizados o incompletos, y no son asesoría legal. Lo que cuenta son
            las normas vigentes de la agencia de pesca y vida silvestre de tu estado y los letreros en el lugar. Eres
            responsable de tener la licencia correcta y de cumplir las normas.
          </li>
          <li>
            <strong>Acceso y terrenos.</strong> Un lago, una rampa, una orilla o un punto en FishEye puede ser privado,
            estar cerrado, ser peligroso o no estar donde lo muestra el mapa. FishEye no es un levantamiento topográfico
            ni indica quién es el dueño de un terreno; un lugar que aparece como público, o que no está marcado como
            privado, puede ser privado. Respeta los letreros, pide permiso antes de pescar en terrenos privados y no
            entres sin autorización.
          </li>
          <li>
            <strong>Datos de peces y lagos.</strong> Qué peces viven en un lago, las siembras, las profundidades y otros
            datos provienen de fuentes públicas y de reportes de pescadores, que pueden estar equivocados o ser antiguos.
          </li>
          <li>
            <strong>No apto para navegación.</strong> Los mapas y las posiciones de FishEye pueden tener errores. No son
            una carta de navegación: no los uses para dirigir una embarcación ni para orientarte, y vigila tú mismo los
            peligros.
          </li>
          <li>
            <strong>Clima, agua y pronósticos.</strong> El clima, los niveles de agua, las puntuaciones de pesca y los
            mejores horarios son estimaciones basadas en datos de otros servicios y en modelos sencillos. Las
            condiciones cambian rápido y pueden ser distintas donde tú estás.
          </li>
          <li>
            <strong>Identificación por foto.</strong> Identificar el pez o el equipo de una foto es una suposición de una
            computadora. No te bases en ella para decidir si un pez se puede conservar legalmente, si está protegido o si
            es seguro manipularlo o comerlo.
          </li>
          <li>
            <strong>Consumo de pescado.</strong> Que el pescado de un cuerpo de agua sea seguro para comer depende de las
            recomendaciones locales sobre consumo de pescado. Consulta las recomendaciones de tu estado antes de comer tu
            captura.
          </li>
          <li>
            <strong>Equipo.</strong> El equipo que se menciona en las guías es un ejemplo, no una recomendación. FishEye
            no vende equipo; úsalo según las indicaciones del fabricante. Si algún enlace llegara a generarle una comisión
            a FishEye, lo indicaremos junto al enlace.
          </li>
          <li>
            <strong>Sin asesoría profesional.</strong> Nada en FishEye constituye asesoría legal, médica, de seguridad ni
            de ningún otro tipo profesional.
          </li>
        </ul>
      </section>

      <section id="ai-answers">
        <Heading id="ai-answers" titles={TITLES} />
        <p>
          Preguntar puede darte una respuesta escrita por un modelo de IA. Es una IA, no una persona, y FishEye la
          identifica como tal.
        </p>
        <ul>
          <li>
            Responde a partir de las guías de FishEye cuando estas cubren tu pregunta, y a partir del conocimiento general
            del propio modelo cuando no la cubren. FishEye no verifica ese conocimiento. Una respuesta puede ser
            incorrecta, incompleta, estar desactualizada o no corresponder a tu cuerpo de agua, estado o temporada, y la
            IA no puede ver las condiciones donde estás.
          </li>
          <li className="legal-conspicuous">
            Usas las respuestas de IA bajo tu propio riesgo. No te bases en ellas para nada que afecte tu seguridad, tu
            salud o la ley, y usa tu propio criterio para decidir si sus consejos son seguros y adecuados para tu nivel.
            Para normas, licencias y límites, acude a la agencia de pesca y vida silvestre de tu estado.
          </li>
          <li>
            Si tienes menos de 18 años, usa las respuestas de IA con la participación de tu madre, padre o tutor.
          </li>
          <li>
            Pregúntale a la IA sobre pesca. No la uses para crear contenido dañino, ilegal u ofensivo, para eludir sus
            límites ni para recopilar respuestas de forma masiva.
          </li>
          <li>
            Para escribir una respuesta, tu pregunta y los pasajes de las guías que coinciden con ella se envían a
            nuestro proveedor de IA, Anthropic. No incluyas información personal, tuya ni de nadie más, en una pregunta.
            Consulta la <Link href="/privacy">política de privacidad</Link>.
          </li>
          <li>
            Una cuenta gratuita recibe un número determinado de respuestas de IA al día, que se muestra junto al botón.
            FishEye Plus no tiene límite diario para uso personal; podemos ralentizar o pausar las respuestas de IA de
            una cuenta cuyo uso parezca automatizado o abusivo.
          </li>
          <li>
            Es posible que las respuestas de IA no estén disponibles en algunos momentos, por ejemplo, cuando nuestro
            proveedor tiene una falla o cuando FishEye las pausa. Podemos cambiar, limitar o suspender las respuestas de
            IA en cualquier momento.
          </li>
          <li>
            Puedes usar las respuestas que recibas para tu propia pesca. Si compartes una, verifícala primero e indica
            que proviene de una IA. Otra persona que haga la misma pregunta puede recibir la misma respuesta o una
            similar.
          </li>
        </ul>
      </section>

      <section id="plus">
        <Heading id="plus" titles={TITLES} />
        <p>
          FishEye Plus es una membresía. Lo que incluye se describe donde la obtienes; hoy elimina el límite diario de
          respuestas de IA. FishEye también puede ofrecer Plus gratis a algunas cuentas.
        </p>
        <ul>
          <li>
            <strong>Antes de pagar</strong>, verás el precio, con qué frecuencia se te cobrará, que se renueva
            automáticamente y cómo cancelarla. Al comprar, autorizas ese cargo y cada renovación hasta que la canceles.
          </li>
          <li>
            <strong>Renovación.</strong> Plus se renueva automáticamente al final de cada período, al precio vigente en
            ese momento, hasta que la canceles. Antes de que se renueve una membresía anual, te recordaremos el precio y
            cómo cancelarla.
          </li>
          <li>
            <strong>Cancelación.</strong> Puedes cancelar en cualquier momento: en la configuración de tu cuenta de Apple
            o Google si compraste Plus en la app (eliminar la app no la cancela), o en tu{" "}
            <Link href="/account">página de cuenta</Link> si la compraste en el sitio web. Al cancelar se detiene la
            siguiente renovación; conservas Plus hasta el final del período que pagaste.
          </li>
          <li>
            <strong>Pruebas gratuitas.</strong> Si inicias una prueba gratuita, se convierte en una membresía de pago
            cuando termina, salvo que la canceles antes. Te indicaremos la fecha cuando la inicies.
          </li>
          <li>
            <strong>Cambios de precio.</strong> Podemos cambiar el precio de Plus. Te avisaremos antes de que se te
            aplique un nuevo precio, con tiempo para cancelar primero.
          </li>
          <li>
            <strong>Reembolsos.</strong> Los pagos no son reembolsables, ni tampoco los períodos parciales, salvo cuando
            la ley lo exija o indiquemos otra cosa. Las compras hechas a través de Apple o Google solo se reembolsan
            según sus políticas; solicítalo a ellos.
          </li>
          <li>
            <strong>Si dejamos de ofrecer Plus</strong>, o cerramos tu cuenta sin que hayas incumplido estos términos, te
            reembolsaremos la parte no utilizada del período que pagaste.
          </li>
          <li>
            <strong>El Plus gratuito</strong> dura el tiempo indicado, no tiene valor en efectivo y no se puede
            transferir.
          </li>
          <li>Es posible que los precios no incluyan impuestos. Tú pagas los impuestos que correspondan.</li>
        </ul>
      </section>

      <section id="your-content">
        <Heading id="your-content" titles={TITLES} />
        <p>
          Conservas la propiedad de las capturas, fotos, notas y comentarios que publicas. Para que FishEye pueda
          funcionar, le otorgas a FishEye una licencia mundial, no exclusiva y libre de regalías para almacenarlos,
          copiarlos (por ejemplo, como versiones más pequeñas de una foto o en copias de seguridad) y mostrarlos en
          FishEye: a todos, si la captura o el comentario es público, y solo a ti (y a los moderadores), si es privado.
          La licencia termina cuando eliminas el contenido o tu cuenta, salvo por las copias de seguridad, que se
          reemplazan con el tiempo.
        </p>
        <ul>
          <li>
            Eres responsable de lo que publicas. Publica solo fotos que hayas tomado tú o que tengas permiso para usar, y
            no publiques fotos de otras personas sin su consentimiento ni información personal de nadie.
          </li>
          <li>
            Cuando publicas una captura, eliges quién la ve y qué tan exacta es su ubicación. Aun así, una foto puede
            revelar un lugar, así que piénsalo antes de publicarla. No publiques un punto que lleve a la gente a terrenos
            privados.
          </li>
          <li>
            No revisamos el contenido antes de que aparezca y no respaldamos lo que publican otros pescadores. Sus
            capturas y comentarios son suyos y pueden estar equivocados. Tampoco verificamos la identidad de otros
            pescadores: usa el sentido común antes de reunirte con alguien a quien solo conoces por FishEye.
          </li>
          <li>Si nos envías ideas o comentarios, podemos usarlos libremente, sin pagarte ni deberte nada.</li>
        </ul>
      </section>

      <section id="rules">
        <Heading id="rules" titles={TITLES} />
        <p>No uses FishEye para:</p>
        <ul>
          <li>
            infringir la ley, incluidas las leyes de pesca, vida silvestre, navegación e invasión de propiedad, ni para
            mostrarte haciéndolo o animar a otros a hacerlo;
          </li>
          <li>acosar, amenazar, acechar o suplantar a cualquier persona, ni publicar información personal de otra persona;</li>
          <li>
            usar insultos o atacar a personas por su raza, origen étnico, nacionalidad, religión, sexo, orientación
            sexual, identidad de género, edad o discapacidad (no se aceptan nombres ni capturas con insultos);
          </li>
          <li>
            publicar spam, publicidad, contenido sexual, violencia gratuita o contenido sangriento, ni nada que no tengas
            derecho a publicar. Todo contenido que sexualice a un menor se elimina y se denuncia ante las autoridades;
          </li>
          <li>marcar un lugar para engañar a la gente, ni dirigir a personas a terrenos privados sin permiso;</li>
          <li>
            recopilar datos de FishEye con bots o scrapers, copiar sus guías o datos de forma masiva, usarlos para
            entrenar modelos de IA ni crear con ellos un servicio competidor;
          </li>
          <li>
            crear cuentas adicionales, compartir o vender una cuenta, ni eludir los límites, las suspensiones o la
            seguridad de FishEye;
          </li>
          <li>
            sondear, dañar o sobrecargar los sistemas de FishEye, subir malware ni aplicar ingeniería inversa a FishEye,
            salvo donde la ley lo permita;
          </li>
          <li>intentar que la IA produzca contenido dañino o ignore sus instrucciones.</li>
        </ul>
      </section>

      <section id="moderation">
        <Heading id="moderation" titles={TITLES} />
        <ul>
          <li>
            Cualquier persona con una cuenta puede denunciar una captura o un comentario públicos. Los moderadores pueden
            ocultar o eliminar contenido, limitar funciones, o suspender o cerrar cuentas que incumplan estos términos,
            cuando la ley lo exija o para proteger a las personas o a FishEye. Por lo general explicamos el motivo, salvo
            que la ley o la seguridad de alguien nos lo impida. Si crees que nos equivocamos, escríbenos.
          </li>
          <li>
            Puedes eliminar tu cuenta en cualquier momento desde tu <Link href="/account">página de cuenta</Link>.
            Eliminar tu cuenta no cancela Plus comprado a través de Apple o Google; cancélalo allí.
          </li>
          <li>
            Las secciones {sec("your-content")} (la licencia sobre lo que compartiste, hasta que se elimine) y{" "}
            {sec("our-content")} a {sec("general")} siguen vigentes después del cierre de tu cuenta.
          </li>
        </ul>
      </section>

      <section id="our-content">
        <Heading id="our-content" titles={TITLES} />
        <p>
          Las guías, los textos, el diseño, el código, el nombre y el logotipo de FishEye, así como la forma en que se
          organizan sus datos, pertenecen a FishEye o a quienes nos otorgan licencias sobre ellos. Te otorgamos una
          licencia personal, no comercial e intransferible para usar FishEye conforme a estos términos, que termina si
          los incumples. Comparte enlaces libremente y cita fragmentos breves dando crédito; no copies las guías ni los
          datos de forma masiva, no los vendas ni los presentes como tuyos.
        </p>
      </section>

      <section id="third-parties">
        <Heading id="third-parties" titles={TITLES} />
        <ul>
          <li>
            FishEye usa datos públicos de agencias gubernamentales y proyectos abiertos, con el crédito correspondiente
            donde aparecen y en la página de <Link href="/sources">fuentes</Link>. Los datos del mapa son © colaboradores
            de OpenStreetMap; los mapas son de MapTiler; las fotos de peces provienen de Wikimedia Commons bajo sus
            propias licencias. Sus licencias y términos se aplican a esos datos.
          </li>
          <li>
            Los enlaces a sitios web de agencias y a otros sitios se ofrecen para tu comodidad. No controlamos esos sitios
            y no somos responsables de ellos.
          </li>
          <li>
            Los servicios que usas con FishEye, como Iniciar sesión con Google, la App Store de Apple, Google Play y tu
            plan de datos móviles, tienen sus propios términos. Debes cumplirlos cuando uses FishEye.
          </li>
        </ul>
      </section>

      <section id="copyright">
        <Heading id="copyright" titles={TITLES} />
        <p>
          Para denunciar contenido que infrinja tus derechos de autor, o para responder a una denuncia sobre el tuyo,
          consulta <Link href="/copyright">Derechos de autor y contenido</Link>. Cerramos las cuentas de quienes infringen
          derechos de forma reiterada.
        </p>
      </section>

      <section id="safety">
        <Heading id="safety" titles={TITLES} />
        <p>
          Pescar, navegar, vadear, pescar en hielo y llegar hasta el agua conllevan riesgos reales, como ahogamiento,
          agua fría, hipotermia, caídas, rayos, calor, anzuelos y cuchillos, fauna silvestre y accidentes en la
          carretera. FishEye no puede ver las condiciones donde estás.
        </p>
        <ul>
          <li>
            Solo tú decides si vas, adónde, cuándo y cómo, y eres responsable de tu propia seguridad y de la de quienes te
            acompañan, en especial los niños.
          </li>
          <li>
            Revisa el clima y el agua, cuéntale a alguien tu plan, usa chaleco salvavidas en una embarcación y cerca de
            aguas profundas o rápidas, y no pises hielo del que no estés seguro.
          </li>
          <li>FishEye no es un servicio de emergencias. En caso de emergencia, llama al 911.</li>
        </ul>
        <p className="legal-conspicuous">
          En la máxima medida permitida por la ley, asumes todos los riesgos de tus actividades de pesca, navegación,
          viaje y otras, incluidos los riesgos que no puedas prever y los que surjan de confiar en FishEye.
        </p>
      </section>

      <section id="disclaimers">
        <Heading id="disclaimers" titles={TITLES} />
        <p className="legal-conspicuous">
          FishEye se ofrece “tal cual” y “según disponibilidad”. En la máxima medida permitida por la ley, FishEye no
          ofrece promesas ni garantías de ningún tipo, expresas o implícitas, sobre FishEye o cualquier cosa que
          contenga, incluidos su información, mapas, pronósticos, respuestas de IA, identificaciones por foto y el
          contenido de otras personas. Esto incluye cualquier promesa de que sean exactos, completos, actuales,
          confiables, seguros, disponibles, ininterrumpidos o libres de errores, y las garantías implícitas de
          comerciabilidad, idoneidad para un fin determinado, titularidad y no infracción.
        </p>
        <p>
          Algunos lugares no permiten algunas de estas exclusiones. Allí, se aplican en la medida en que la ley lo
          permita.
        </p>
      </section>

      <section id="liability">
        <Heading id="liability" titles={TITLES} />
        <p>
          En estos términos, “el equipo de FishEye” significa FishEye, su operador y las personas que trabajan en
          FishEye o para FishEye.
        </p>
        <div className="legal-conspicuous">
          <p>En la máxima medida permitida por la ley:</p>
          <ul>
            <li>
              el equipo de FishEye no es responsable de daños indirectos, incidentales, especiales, consecuentes,
              ejemplares o punitivos, ni de la pérdida de ganancias, datos o prestigio comercial, aunque se le haya
              advertido de su posibilidad;
            </li>
            <li>
              el equipo de FishEye no es responsable de nada que ocurra mientras pescas, navegas o viajas, ni en un lugar
              que encontraste en FishEye o a través de FishEye; de multas o sanciones; ni de las decisiones que tomes con
              base en la información o las respuestas de IA de FishEye;
            </li>
            <li>
              la responsabilidad total del equipo de FishEye por todas las reclamaciones relacionadas con FishEye o con
              estos términos se limita al monto mayor entre US${LEGAL.liabilityFloorUsd} y lo que le hayas pagado a
              FishEye en los 12 meses anteriores al surgimiento de la reclamación.
            </li>
          </ul>
          <p>
            Estos límites se aplican sin importar la teoría jurídica: contrato, garantía, negligencia, responsabilidad
            objetiva o cualquier otra.
          </p>
        </div>
        <p>
          No limitan la responsabilidad por negligencia grave, conducta dolosa o fraude, ni ninguna responsabilidad que
          la ley no permita limitar. Algunos lugares no permiten estos límites, por lo que es posible que no todos se
          apliquen a ti.
        </p>
      </section>

      <section id="release">
        <Heading id="release" titles={TITLES} />
        <p className="legal-conspicuous">
          En la máxima medida permitida por la ley, liberas al equipo de FishEye de todas las reclamaciones, conocidas o
          desconocidas, por lesiones, muerte, daños a la propiedad u otras pérdidas que surjan de tus actividades de
          pesca, navegación, viaje u otras, de confiar en la información, los mapas, los pronósticos o las respuestas de
          IA de FishEye, o de tus disputas con otros pescadores o con cualquier otra persona (como el dueño de un
          terreno), incluidas las reclamaciones basadas en la negligencia del equipo de FishEye, y te comprometes a no
          demandarlos por dichas reclamaciones. Esta renuncia no abarca la negligencia grave ni la conducta dolosa.
        </p>
        <p>
          Si vives en California, renuncias a la sección 1542 del Código Civil de California, que establece: “Una
          renuncia general no se extiende a las reclamaciones que el acreedor o la parte que otorga la renuncia no conozca
          o no sospeche que existen a su favor en el momento de firmar la renuncia y que, de haberlas conocido, habrían
          afectado sustancialmente su acuerdo con el deudor o la parte liberada”. También renuncias a cualquier ley
          similar de otros lugares.
        </p>
      </section>

      <section id="indemnity">
        <Heading id="indemnity" titles={TITLES} />
        <p>
          En la medida en que la ley lo permita, defenderás e indemnizarás al equipo de FishEye frente a reclamaciones de
          terceros, y las pérdidas, los costos y los honorarios razonables de abogados que conlleven, que surjan de lo que
          publiques, de tu incumplimiento de estos términos o de la ley, o de tus actividades de pesca u otras (por
          ejemplo, entrar sin autorización en un punto que marcaste). Te informaremos de cualquier reclamación de ese
          tipo, podremos optar por encargarnos nosotros de la defensa y nos ayudarás en lo que sea razonablemente
          necesario.
        </p>
      </section>

      <section id="disputes">
        <Heading id="disputes" titles={TITLES} />
        <p className="legal-conspicuous">
          Lee esta sección con atención. Afecta tus derechos, incluido tu derecho a acudir a los tribunales.
        </p>
        <p>
          <strong>Habla primero con nosotros.</strong> La mayoría de los problemas se resuelven conversando. Antes de
          iniciar un arbitraje o un proceso judicial, envía un aviso a{" "}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a> con el asunto “Dispute” (disputa), con tu
          nombre, el correo electrónico de tu cuenta, lo que ocurrió y lo que solicitas. Nosotros enviaremos el nuestro al
          correo electrónico de tu cuenta. Después, ambas partes intentarán de buena fe resolverlo durante 60 días, y
          cualquier plazo para la reclamación se suspende mientras tanto.
        </p>
        <p>
          <strong>Arbitraje.</strong> Si no se resuelve, tú y FishEye acuerdan que cualquier disputa o reclamación que
          surja de estos términos o de FishEye, o que esté relacionada con ellos (una “reclamación”), se resolverá
          mediante arbitraje vinculante ante un único árbitro, de forma individual y no ante un tribunal, con las
          siguientes excepciones:
        </p>
        <ul>
          <li>
            cualquiera de las partes puede presentar una reclamación individual en un tribunal de reclamos menores, si
            reúne los requisitos;
          </li>
          <li>
            cualquiera de las partes puede pedir a un tribunal que detenga la infracción o el uso indebido de su propiedad
            intelectual;
          </li>
          <li>este párrafo no se aplica si te excluyes, como se describe más adelante.</li>
        </ul>
        <p>
          Esta sección se rige por la Ley Federal de Arbitraje. La Asociación Americana de Arbitraje (AAA) administra el
          arbitraje conforme a sus Reglas de Arbitraje de Consumo y, cuando correspondan, sus reglas para arbitrajes
          masivos (consulta adr.org). El árbitro puede otorgarte la misma reparación individual que podría otorgar un
          tribunal. En una reclamación que tú presentes, FishEye paga las tarifas de presentación, de administración y
          del árbitro de la AAA que excedan lo que te costaría presentar la demanda ante un tribunal, salvo que el árbitro
          determine que tu reclamación es frívola. Cualquier audiencia se realiza por video o por teléfono o, si lo
          prefieres, en persona en el condado donde vives.
        </p>
        <p className="legal-conspicuous">
          Sin demandas colectivas. Tú y FishEye solo pueden presentar reclamaciones entre sí de forma individual, y no
          como demandante o miembro de ningún procedimiento colectivo, de grupo, acumulado o representativo. Si se
          determina que esta oración no es exigible para una reclamación, esa reclamación se resolverá ante un tribunal en
          lugar de mediante arbitraje. Si la ley no permite que una solicitud de medidas cautelares de interés público se
          someta a arbitraje, esa solicitud se presentará ante un tribunal una vez concluido el arbitraje individual. Si
          una reclamación se resuelve ante un tribunal, tú y FishEye renuncian cada uno a un juicio con jurado, en la
          medida en que la ley lo permita.
        </p>
        <p>
          <strong>Exclusión.</strong> Puedes excluirte del arbitraje en un plazo de {optOut} días desde que aceptes estos
          términos por primera vez: envía un correo a <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>{" "}
          con el asunto “Arbitration opt-out” (exclusión del arbitraje), tu nombre y el correo electrónico de tu cuenta.
          Excluirte no cambia nada más de estos términos.
        </p>
        <p>
          <strong>Cambios en esta sección.</strong> Un cambio en esta sección no se aplica a una reclamación que
          cualquiera de las partes ya haya notificado. Si hacemos un cambio importante, puedes rechazarlo en un plazo de 30
          días enviándonos un correo, y la versión anterior seguirá aplicándose a ti.
        </p>
        <p>
          <strong>Plazo.</strong> En la medida en que la ley lo permita, una reclamación debe iniciarse dentro de los dos
          años posteriores a su surgimiento; de lo contrario, no podrá presentarse.
        </p>
        <p>
          <strong>Ley y tribunales.</strong> Estos términos se rigen por las leyes del estado de {LEGAL.governingState},
          sin tener en cuenta las normas sobre conflicto de leyes, y por la Ley Federal de Arbitraje en lo que respecta a
          esta sección. Una reclamación que no se someta a arbitraje se presentará ante los tribunales estatales o
          federales ubicados en {LEGAL.governingState}, y tú y FishEye aceptan su jurisdicción, salvo que la ley del lugar
          donde vives te otorgue el derecho a presentarla allí.
        </p>
      </section>

      <section id="changes">
        <Heading id="changes" titles={TITLES} />
        <ul>
          <li>
            Podemos cambiar FishEye, agregar o quitar funciones, o dejar de ofrecerlo. Si dejamos de ofrecer algo por lo
            que pagaste, la sección {sec("plus")} indica lo que recibes a cambio.
          </li>
          <li>
            Podemos cambiar estos términos. Actualizamos la fecha que aparece arriba y, si se trata de un cambio
            importante, te avisamos en el sitio o por correo electrónico al menos {LEGAL.noticeDays} días antes de que se
            aplique, salvo que la ley exija un cambio antes o que se trate de una función nueva. Si sigues usando FishEye
            después de que un cambio entre en vigor, lo aceptas. Si no lo aceptas, deja de usar FishEye y elimina tu
            cuenta.
          </li>
          <li>
            Las funciones marcadas como nuevas o de prueba pueden tener más errores que el resto, y pueden cambiar o
            desaparecer.
          </li>
        </ul>
      </section>

      <section id="app-stores">
        <Heading id="app-stores" titles={TITLES} />
        <p>Si obtuviste la app de FishEye en la App Store de Apple:</p>
        <ul>
          <li>
            Estos términos son solo entre tú y FishEye, no Apple. FishEye, y no Apple, es responsable de la app y de su
            contenido.
          </li>
          <li>
            Tu licencia sobre la app es intransferible y se limita a su uso en productos de la marca Apple que poseas o
            controles, según lo permitan las Reglas de uso de los Términos y condiciones de los Servicios Multimedia de
            Apple (incluido En familia). Cuando estos términos contradigan esas Reglas de uso, las Reglas de uso se
            aplican a la app.
          </li>
          <li>
            FishEye, y no Apple, presta cualquier servicio de mantenimiento y soporte de la app. Apple no tiene ninguna
            obligación de hacerlo.
          </li>
          <li>
            Si la app no cumple alguna garantía aplicable, puedes notificarlo a Apple, y Apple te reembolsará el precio de
            compra de la app, si lo hubiera. En la medida en que la ley lo permita, Apple no tiene ninguna otra obligación
            de garantía respecto a la app, y cualquier otra reclamación, pérdida o costo derivado de dicho incumplimiento
            es responsabilidad de FishEye, en la medida en que no se haya excluido en estos términos.
          </li>
          <li>
            FishEye, y no Apple, es responsable de cualquier reclamación relacionada con la app o con tu uso de ella,
            incluidas las reclamaciones por responsabilidad del producto, las reclamaciones de que no cumple algún
            requisito legal o reglamentario, y las reclamaciones en virtud de leyes de protección al consumidor, de
            privacidad o similares.
          </li>
          <li>
            Si alguien afirma que la app o tu uso de ella infringe su propiedad intelectual, FishEye, y no Apple, es
            responsable de investigar, defender, resolver y liquidar la reclamación.
          </li>
          <li>
            Apple y sus subsidiarias son terceros beneficiarios de estos términos. Una vez que los aceptes, Apple podrá
            hacerlos valer frente a ti.
          </li>
        </ul>
        <p>
          Si obtuviste la app en Google Play, los términos de Google rigen tu compra y Google no es responsable de la app.
        </p>
      </section>

      <section id="general">
        <Heading id="general" titles={TITLES} />
        <ul>
          <li>
            Estos términos, la política de privacidad, la página de derechos de autor y cualquier término que se muestre
            para una función específica constituyen el acuerdo completo entre tú y FishEye sobre FishEye.
          </li>
          <li>
            Si alguna parte de estos términos no puede hacerse cumplir, se modificará lo mínimo necesario para que sea
            exigible, y el resto seguirá vigente. Si no hacemos cumplir alguna parte, no significa que renunciemos a
            ella.
          </li>
          <li>
            No puedes transferir estos términos ni tu cuenta. Nosotros podemos transferirlos, por ejemplo, a una empresa
            que se haga cargo de FishEye, o en caso de fusión o venta.
          </li>
          <li>No somos responsables de retrasos o incumplimientos causados por hechos fuera de nuestro control razonable.</li>
          <li>
            Estos términos no hacen de ti y de FishEye socios, empleador y empleado, ni agentes el uno del otro. Nadie más
            puede hacerlos valer, excepto el equipo de FishEye (secciones {sec("liability")} a {sec("indemnity")}) y
            Apple (sección {sec("app-stores")}).
          </li>
          <li>
            Podemos enviarte avisos por correo electrónico a la dirección de tu cuenta o en FishEye, y aceptas que los
            avisos y acuerdos electrónicos tienen la misma validez que los escritos. Puedes enviarnos avisos a los datos
            de contacto que aparecen abajo.
          </li>
          <li>
            Estos términos están redactados en inglés. Cualquier traducción se ofrece por comodidad; la versión en inglés
            es la que se aplica. “Incluido” significa “incluido, entre otros”.
          </li>
          <li>
            Residentes de California: pueden comunicarse por escrito con la Unidad de Asistencia de Quejas de la División
            de Servicios al Consumidor del Departamento de Asuntos del Consumidor de California en 1625 North Market
            Blvd., Suite N 112, Sacramento, CA 95834, o por teléfono al (800) 952-5210.
          </li>
        </ul>
      </section>

      <section id="contact">
        <Heading id="contact" titles={TITLES} />
        <p>
          {LEGAL.operator && (
            <>
              {LEGAL.operator}
              <br />
            </>
          )}
          {LEGAL.mailingAddress && (
            <>
              {LEGAL.mailingAddress}
              <br />
            </>
          )}
          <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>
        </p>
        <p>Las preguntas, quejas y reclamaciones sobre FishEye o la app se envían a esta dirección de correo electrónico.</p>
      </section>
    </>
  );
}

export const es: TermsText = {
  title: "Términos de uso",
  lede: "El acuerdo entre tú y FishEye. Léelo: te pide que asumas la responsabilidad de tu propia seguridad, limita la responsabilidad de FishEye y lleva la mayoría de las disputas a arbitraje individual.",
  description: "El acuerdo para usar FishEye: información de pesca, respuestas de IA, FishEye Plus, lo que compartes y las disputas.",
  Body,
};
