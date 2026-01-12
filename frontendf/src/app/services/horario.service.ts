import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Horario } from '../models';

@Injectable({
  providedIn: 'root'
})
export class HorarioService {

  constructor(private apiService: ApiService) { }

  getHorarios(): Observable<Horario[]> {
    return this.apiService.get<Horario[]>('/horarios/');
  }

  getHorario(id: number): Observable<Horario> {
    return this.apiService.get<Horario>(`/horarios/${id}/`);
  }

  createHorario(horario: Horario): Observable<Horario> {
    return this.apiService.post<Horario>('/horarios/', horario);
  }

  updateHorario(id: number, horario: Horario): Observable<Horario> {
    return this.apiService.put<Horario>(`/horarios/${id}/`, horario);
  }

  deleteHorario(id: number): Observable<any> {
    return this.apiService.delete(`/horarios/${id}/`);
  }
}
