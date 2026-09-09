import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface EventualDatos {
  persona_id: number;
  cedula: string;
  nombres: string;
  apellidos: string;
  tipo: string;
  fecha_ingreso: string | null;
  provincia_id: number | null;
  provincia_nombre: string;
  canton_id: number | null;
  canton_nombre: string;
  banco: string;
  numero_cuenta: string;
  tipo_cuenta: string;   // AHORROS | CORRIENTE | DIGITAL | ''
}

export interface EventualListItem {
  persona_id: number;
  cedula: string;
  nombres: string;
  apellidos: string;
  fecha_ingreso: string | null;
  provincia_nombre: string;
  canton_nombre: string;
  banco: string;
  numero_cuenta: string;
  tipo_cuenta: string;
}

@Injectable({ providedIn: 'root' })
export class EventualService {
  constructor(private api: ApiService) {}

  /** Lista de todos los eventuales (base). */
  listar(): Observable<{ results: EventualListItem[]; total: number }> {
    return this.api.get<{ results: EventualListItem[]; total: number }>('/asignaciones/eventuales/');
  }

  /** Trae los datos del eventual para el modal. */
  obtener(personaId: number): Observable<EventualDatos> {
    return this.api.get<EventualDatos>(`/asignaciones/eventual/${personaId}/`);
  }

  /** Guarda los cambios del modal. */
  guardar(personaId: number, data: Partial<EventualDatos>): Observable<EventualDatos> {
    return this.api.put<EventualDatos>(`/asignaciones/eventual/${personaId}/`, data);
  }
}
