import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable, of, tap } from 'rxjs';
import { Persona } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PersonaService {
  private cache: Persona[] | null = null;

  constructor(private apiService: ApiService) { }

  getPersonas(forceRefresh: boolean = false): Observable<Persona[]>{
    if (!forceRefresh && this.cache) {
      return of(this.cache);
    }
    return this.apiService.get<Persona[]>('/personas/').pipe(
      tap(data => this.cache = data)
    );
  }

  getPersona(id: number): Observable<Persona>{
    return this.apiService.get<Persona>(`/personas/${id}/`);
  }

  createPersona(persona: Persona): Observable<Persona>{
    this.cache = null; // Invalidar caché
    return this.apiService.post<Persona>('/crear-persona/', persona);
  }

  updatePersona(id: number, persona: Persona): Observable<Persona>{
    this.cache = null; // Invalidar caché
    return this.apiService.put<Persona>(`/actualizar-persona/${id}/`, persona);
  }

  deletePersona(id: number): Observable<any>{
    this.cache = null; // Invalidar caché
    return this.apiService.delete(`/eliminar-persona/${id}/`);
  }

}
