import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { ApiService } from './api.service';
import { Asignacion, SacafrancoFila } from '../models/asignacion.model';
import { map } from 'rxjs/operators';
import { environment } from '@env/environment';

@Injectable({
  providedIn: 'root'
})
export class AsignacionService {
  private apiUrl = environment.apiUrl;

  // Notifica cuando cambian las asignaciones (crear/editar/eliminar) para refrescar contadores.
  private asignacionesChanged = new Subject<void>();
  asignacionesChanged$ = this.asignacionesChanged.asObservable();

  notifyAsignacionesChanged(): void {
    this.asignacionesChanged.next();
  }

  // Canal para pedir a la vista de asignaciones que abra un puesto vacante específico.
  private abrirAsignacion = new Subject<{ id: number; cantonId: number | null }>();
  abrirAsignacion$ = this.abrirAsignacion.asObservable();

  solicitarAbrirAsignacion(id: number, cantonId: number | null): void {
    this.abrirAsignacion.next({ id, cantonId });
  }

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

  obtenerAsignacionesPaginadas(mes: number, anio: number, params?: any): Observable<{ results: Asignacion[]; total: number; page: number; size: number; provinciaTotal?: number; provinciaPage?: number; provinciaId?: number | null; cantonTotal?: number; cantonPage?: number; cantonId?: number | null; cantonOptions?: Array<{ id: number | null; nombre: string }> }> {
    return this.apiService.get<any>(`/asignaciones/${mes}/${anio}/`, params).pipe(
      map(response => {
        const raw = Array.isArray(response) ? response : (response?.results || []);
        const results = raw.map((asig: any) => ({
          ...asig,
          instalacionCodigo: asig.instalacionCodigo || (asig.instalacion_detalle ? asig.instalacion_detalle.codigo : '')
        }));
        const cantonTotal = response?.canton_total ?? response?.provincia_total;
        const cantonPage = response?.canton_page ?? response?.provincia_page;
        const cantonId = response?.canton_id ?? response?.provincia_id;
        return {
          results,
          total: Array.isArray(response) ? results.length : (response?.total ?? results.length),
          page: Array.isArray(response) ? 1 : (response?.page ?? cantonPage ?? 1),
          size: Array.isArray(response) ? results.length : (response?.size ?? results.length)
        ,
          provinciaTotal: cantonTotal,
          provinciaPage: cantonPage,
          provinciaId: cantonId,
          cantonTotal,
          cantonPage,
          cantonId,
          cantonOptions: response?.canton_options
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

  guardarOrden(ordenes: {id: number, orden: number}[], mes?: number, anio?: number): Observable<any>{
    return this.apiService.post<any>(`/guardar-orden-asignacion/`, { ordenes, mes, anio });
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

  obtenerPersonasAsignadas(mes: number, anio: number): Observable<number[]> {
    return this.apiService.get<any>(`/personas-asignadas/${mes}/${anio}/`).pipe(
      map(response => (response?.persona_ids ?? []) as number[])
    );
  }

  // Conteo de cupos ocupados por puesto en el mes (todos los cantones).
  obtenerPuestosOcupacion(mes: number, anio: number): Observable<{ [puestoId: number]: number }> {
    return this.apiService.get<any>(`/puestos-ocupacion/${mes}/${anio}/`).pipe(
      map(response => (response?.ocupacion ?? {}) as { [puestoId: number]: number })
    );
  }

  obtenerAsignacionesVacantes(mes: number, anio: number): Observable<{ total: number; results: Array<{ id: number; codigo: string; cliente: string; instalacion: string; puesto: string; canton: string; canton_id: number | null; horario: string }> }> {
    return this.apiService.get<any>(`/asignaciones-vacantes/${mes}/${anio}/`).pipe(
      map(response => ({
        total: response?.total ?? 0,
        results: response?.results ?? []
      }))
    );
  }

  // Vistas compartidas (guardadas en BD, visibles para todos los usuarios).
  obtenerVistasCantones(): Observable<any[]> {
    return this.apiService.get<any>('/vistas-cantones/').pipe(
      map(r => (Array.isArray(r) ? r : (r?.views ?? [])))
    );
  }

  guardarVistasCantones(views: any[]): Observable<any[]> {
    return this.apiService.post<any>('/vistas-cantones/', { views }).pipe(
      map(r => (Array.isArray(r) ? r : (r?.views ?? [])))
    );
  }

}
