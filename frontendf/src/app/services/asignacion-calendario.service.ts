import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Injectable } from '@angular/core';
import { AsignacionSemanal, SacafrancoFilaSemanal } from '../models/asignacion-calendario';

@Injectable({
  providedIn: 'root'
})
export class AsignacionCalendarioService {
  constructor(private apiService: ApiService){}

  obtenerAsignacionesCalendario(params?: any): Observable<any>{
    return this.apiService.get<any>('/asignacion-semanal/', params);
  }

  obtenerAsignacionesCalendarioMes(mes: number, anio: number, params?: any): Observable<any>{
    return this.apiService.get<any>('/asignacion-semanal/mes/', { mes, anio, ...(params || {}) });
  }

  obtenerSemanas(mes: number, anio: number): Observable<any>{
    return this.apiService.get<any>('/semanas/', { mes, anio });
  }

  crearAsignacionCalendario(asignacion: AsignacionSemanal): Observable<any>{
    return this.apiService.post<any>('/asignacion-semanal/guardar/', asignacion);
  }

  obtenerSacafrancoFilaSemanal(params?: any): Observable<SacafrancoFilaSemanal[]>{
    return this.apiService.get<SacafrancoFilaSemanal[]>('/sacafranco-fila-semanal/', params);
  }

  crearSacafrancoFilaSemanal(payload: SacafrancoFilaSemanal): Observable<any>{
    return this.apiService.post<any>('/sacafranco-fila-semanal/guardar/', payload);
  }

}
