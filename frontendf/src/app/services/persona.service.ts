import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { Persona } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PersonaService {

  constructor(private apiService: ApiService) { }

  getPersonas(): Observable<Persona[]>{
    return this.apiService.get<Persona[]>('/personas/');
  }

  getPersona(id: number): Observable<Persona>{
    return this.apiService.get<Persona>(`/personas/${id}/`);
  }

  createPersona(persona: Persona): Observable<Persona>{
    return this.apiService.post<Persona>('/crear-persona/', persona);
  }

  updatePersona(id: number, persona: Persona): Observable<Persona>{
    return this.apiService.put<Persona>(`/actualizar-persona/${id}/`, persona);
  }

  deletePersona(id: number): Observable<any>{
    return this.apiService.delete(`/eliminar-persona/${id}/`);
  }

  disablePersona(id: number): Observable<any>{
    return this.apiService.post(`/disable-persona/${id}/`, {});
  }

  enablePersona(id: number): Observable<any>{
    return this.apiService.post(`/enable-persona/${id}/`, {});
  }

}
