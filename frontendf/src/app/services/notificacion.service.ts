import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface EventualPendiente {
  id: number;            // id de la persona
  cedula: string;
  nombres: string;
  apellidos: string;
  tipo: string;
  validado?: boolean | null;
}

export interface NotificacionEventual {
  id: number;            // id de la notificación
  mensaje: string;
  leida: boolean;
  resuelta: boolean;
  creada_en: string | null;
  creada_por: string | null;
  persona: EventualPendiente | null;
}

export interface CorreccionEventual {
  cedula?: string;
  nombres?: string;
  apellidos?: string;
  tipo?: string;
}

@Injectable({ providedIn: 'root' })
export class NotificacionService {
  constructor(private api: ApiService) {}

  /** Notificaciones pendientes (no resueltas) del usuario en sesión. */
  listarPendientes(): Observable<{ results: NotificacionEventual[]; total: number }> {
    return this.api.get<{ results: NotificacionEventual[]; total: number }>('/notificaciones-eventual/');
  }

  /** Confirma (valida) el eventual, aplicando correcciones opcionales. */
  confirmar(id: number, correccion?: CorreccionEventual): Observable<any> {
    return this.api.post<any>(`/notificaciones-eventual/${id}/confirmar/`, correccion || {});
  }
}
