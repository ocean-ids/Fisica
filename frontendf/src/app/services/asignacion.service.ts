import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Asignacion, SacafrancoFila } from '../models/asignacion.model';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AsignacionService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private apiService: ApiService){}

  obtenerAsignaciones(mes: number, anio: number, params?: any): Observable<Asignacion[]> {
    return this.apiService.get<any>(`/asignaciones/${mes}/${anio}/`, params).pipe(
      map(response => {
        const raw = Array.isArray(response) ? response : (response?.results || []);
        return raw.map((asig: any) => ({
          ...asig,
          instalacionCodigo: asig.instalacionCodigo || (asig.instalacion_detalle ? asig.instalacion_detalle.codigo : '')
        }));
      })
    );
  }

  obtenerAsignacionesPaginadas(mes: number, anio: number, params?: any): Observable<{ results: Asignacion[]; total: number; page: number; size: number; provinciaTotal?: number; provinciaPage?: number; provinciaId?: number | null }> {
    return this.apiService.get<any>(`/asignaciones/${mes}/${anio}/`, params).pipe(
      map(response => {
        const raw = Array.isArray(response) ? response : (response?.results || []);
        const results = raw.map((asig: any) => ({
          ...asig,
          instalacionCodigo: asig.instalacionCodigo || (asig.instalacion_detalle ? asig.instalacion_detalle.codigo : '')
        }));
        return {
          results,
          total: Array.isArray(response) ? results.length : (response?.total ?? results.length),
          page: Array.isArray(response) ? 1 : (response?.page ?? response?.provincia_page ?? 1),
          size: Array.isArray(response) ? results.length : (response?.size ?? results.length)
        ,
          provinciaTotal: response?.provincia_total,
          provinciaPage: response?.provincia_page,
          provinciaId: response?.provincia_id
        };
      })
    );
  }

  crearAsignacion(asignacion: Asignacion): Observable<Asignacion> {
    return this.apiService.post<Asignacion>(`/asignar-servicio/`, asignacion);
  }

  actualizarAsignacion(id: number, asignacion: Partial<Asignacion>): Observable<Asignacion> {
    return this.apiService.put<Asignacion>(`/editar-servicio/${id}/`, asignacion);
  }

  eliminarAsignacion(id: number): Observable<any>{
    return this.apiService.delete<any>(`/eliminar-asignacion/${id}/`);
  }

  guardarOrden(ordenes: {id: number, orden: number}[]): Observable<any>{
    return this.apiService.post<any>(`/guardar-orden-asignacion/`, {ordenes});
  }

  guardarOrdenSacafranco(ordenes: {id: number, orden: number}[]): Observable<any>{
    return this.apiService.post<any>(`/guardar-orden-sacafranco/`, {ordenes});
  }

  obtenerSacafrancoFilas(mes: number, anio: number, params?: any): Observable<SacafrancoFila[]> {
    return this.apiService.get<any>(`/sacafranco-filas/`, { mes, anio, ...(params || {}) }).pipe(
      map(response => Array.isArray(response) ? response : (response?.results || []))
    );
  }

  crearSacafrancoFila(payload: SacafrancoFila): Observable<SacafrancoFila> {
    return this.apiService.post<SacafrancoFila>(`/sacafranco-filas/`, payload);
  }

  eliminarSacafrancoFila(id: number): Observable<any> {
    return this.apiService.delete<any>(`/sacafranco-filas/${id}/`);
  }

  actualizarSacafrancoFila(id: number, payload: Partial<SacafrancoFila>): Observable<SacafrancoFila> {
    return this.apiService.patch<SacafrancoFila>(`/sacafranco-filas/${id}/`, payload);
  }
  
}
