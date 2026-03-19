import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Asignacion } from '../models/asignacion.model';
import {map} from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AsignacionService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private apiService: ApiService){}

  obtenerAsignaciones(mes: number, anio: number, params?: any): Observable<Asignacion[]> {
  return this.apiService.get<any[]>(`/asignaciones/${mes}/${anio}/`, params).pipe(
    map(asignaciones => asignaciones.map(asig => ({
      ...asig,
      instalacionCodigo: asig.instalacionCodigo || (asig.instalacion_detalle ? asig.instalacion_detalle.codigo : '')
    })))
  );
}

  crearAsignacion(asignacion: Asignacion): Observable<Asignacion> {
    return this.apiService.post<Asignacion>(`/asignar-servicio/`, asignacion);
  }

  actualizarAsignacion(id: number, asignacion: Asignacion): Observable<Asignacion> {
    return this.apiService.put<Asignacion>(`/editar-servicio/${id}/`, asignacion);
  }

  eliminarAsignacion(id: number): Observable<any>{
    return this.apiService.delete<any>(`/eliminar-asignacion/${id}/`);
  }

  guardarOrden(ordenes: {id: number, orden: number}[]): Observable<any>{
    return this.apiService.post<any>(`/guardar-orden-asignacion/`, {ordenes});
  }
  
}
