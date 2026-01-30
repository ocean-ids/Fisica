import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Injectable } from '@angular/core';
import { AsignacionSemanal } from '../models/asignacion-calendario';

@Injectable({
  providedIn: 'root'
})
export class AsignacionCalendarioService {
  constructor(private apiService: ApiService){}

  obtenerAsignacionesCalendario(params?: any): Observable<any>{
    return this.apiService.get<any>('/asignacion-semanal/', params);
  }

  crearAsignacionCalendario(asignacion: AsignacionSemanal): Observable<any>{
    return this.apiService.post<any>('/asignacion-semanal/guardar/', asignacion);
  }

  copiarSemana(payload: {from_week: string, to_week: string, cliente?: number}): Observable<any>{
    return this.apiService.post<any>('/asignacion-semanal/copy/', payload);
  }
}
