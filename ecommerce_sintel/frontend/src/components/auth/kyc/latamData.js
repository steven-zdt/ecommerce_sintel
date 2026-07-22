// Catalogos estaticos para minimizar el ingreso manual de datos en el
// registro. "Pais" cubre Latinoamerica; "Ciudad" cubre inicialmente solo
// Colombia (mercado principal de Sintel) -- ampliar por pais cuando haga
// falta, sin romper el contrato de datos existente (pais/ciudad siguen
// siendo strings planos en el payload).

import { COLOMBIA_LOCATIONS } from '@/data/colombiaLocations';

export const DEFAULT_COUNTRY = 'Colombia';

export const LATAM_COUNTRIES = [
  'Colombia', 'Mexico', 'Argentina', 'Peru', 'Chile', 'Ecuador', 'Venezuela',
  'Bolivia', 'Paraguay', 'Uruguay', 'Brasil', 'Panama', 'Costa Rica',
  'Guatemala', 'Honduras', 'El Salvador', 'Nicaragua', 'Republica Dominicana',
  'Cuba', 'Puerto Rico',
];

// Nacionalidad se auto-completa a partir del pais elegido -- ya no es un
// campo manual del formulario (era redundante con "pais").
export const COUNTRY_TO_NATIONALITY = {
  Colombia: 'Colombiana',
  Mexico: 'Mexicana',
  Argentina: 'Argentina',
  Peru: 'Peruana',
  Chile: 'Chilena',
  Ecuador: 'Ecuatoriana',
  Venezuela: 'Venezolana',
  Bolivia: 'Boliviana',
  Paraguay: 'Paraguaya',
  Uruguay: 'Uruguaya',
  Brasil: 'Brasilena',
  Panama: 'Panamena',
  'Costa Rica': 'Costarricense',
  Guatemala: 'Guatemalteca',
  Honduras: 'Hondurena',
  'El Salvador': 'Salvadorena',
  Nicaragua: 'Nicaraguense',
  'Republica Dominicana': 'Dominicana',
  Cuba: 'Cubana',
  'Puerto Rico': 'Puertorriquena',
};

// Derivada del catalogo canonico de departamentos/ciudades (misma fuente que
// usan RentalBookingWizard/ServiceRequestWizard/ColombianAddressForm) en vez
// de mantener una segunda lista manual -- evita que ambas se desincronicen
// (hallazgo real de la auditoria Fase 1/4: 30 ciudades hardcodeadas aqui vs.
// las 33 departamentos/ciudades reales del catalogo canonico).
export const COLOMBIAN_CITIES = Object.values(COLOMBIA_LOCATIONS)
  .flat()
  .sort((a, b) => a.localeCompare(b, 'es'));
