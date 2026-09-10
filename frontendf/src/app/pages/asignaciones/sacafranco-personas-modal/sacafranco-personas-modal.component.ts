import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { Persona } from '../../../models/persona.model';
import { PersonaService } from '../../../services/persona.service';

type SacaResult = { personaId: number | null; cantonId: number | null; horaIngreso: string | null; horaSalida: string | null };

@Component({
  selector: 'app-sacafranco-personas-modal',
  standalone: true,
  imports: [
    CommonModule, FormsModule, ReactiveFormsModule, MatDialogModule, MatFormFieldModule,
    MatInputModule, MatAutocompleteModule, MatButtonModule, MatIconModule,
  ],
  templateUrl: './sacafranco-personas-modal.component.html',
  styleUrl: './sacafranco-personas-modal.component.css'
})
export class SacafrancoPersonasModalComponent implements OnInit {
  personasAll: Persona[] = [];
  personasFiltradas: Persona[] = [];
  selectedId: number | null = null;
  assignedIds = new Set<number>();
  horaIngreso: string = '';
  horaSalida: string = '';
  personaCtrl = new FormControl<Persona | string | null>('');

  constructor(
    private dialogRef: MatDialogRef<SacafrancoPersonasModalComponent, SacaResult | null>,
    private personaService: PersonaService,
    @Inject(MAT_DIALOG_DATA) public data: { personas?: Persona[]; assignedPersonaIds?: number[]; cantones?: Array<{ id: number | null; nombre: string }>; cantonId?: number | null; horaIngreso?: string | null; horaSalida?: string | null; selectedPersonaId?: number | null } | null
  ) {}

  private normalizeText(value: string | null | undefined): string {
    if (!value) return '';
    return value.toString().trim().toUpperCase().normalize('NFD').replace(/[^A-Z0-9]+/g, '');
  }

  private filtrar(q: string): void {
    const tokens = (q || '').trim().split(/\s+/).map(t => this.normalizeText(t)).filter(Boolean);
    if (!tokens.length) { this.personasFiltradas = this.personasAll; return; }
    this.personasFiltradas = this.personasAll.filter(p => {
      const hay = this.normalizeText(`${p.nombres || ''} ${p.apellidos || ''} ${(p as any).cedula || ''}`);
      return tokens.every(t => hay.includes(t));
    });
  }

  ngOnInit(): void {
    if (this.data?.assignedPersonaIds?.length) {
      this.assignedIds = new Set(this.data.assignedPersonaIds);
    }
    this.horaIngreso = (this.data?.horaIngreso || '').toString().slice(0, 5);
    this.horaSalida = (this.data?.horaSalida || '').toString().slice(0, 5);

    const setup = (list: Persona[]) => {
      this.personasAll = (list || []).filter(p => (p.tipo || '').toString().toUpperCase() === 'SACAFRANCO');
      this.personasFiltradas = this.personasAll;
      const preId = this.data?.selectedPersonaId ?? null;
      if (preId) {
        const sel = this.personasAll.find(p => p.id === preId);
        if (sel) { this.selectedId = sel.id ?? null; this.personaCtrl.setValue(sel, { emitEvent: false }); }
      }
    };

    if (this.data?.personas && this.data.personas.length) {
      setup(this.data.personas);
    } else {
      this.personaService.getPersonas({ tipo: 'SACAFRANCO' }).subscribe({
        next: list => setup(list || []),
        error: () => setup([]),
      });
    }

    // Al escribir: filtra y limpia la selección. Al elegir una opción: guarda su id.
    this.personaCtrl.valueChanges.subscribe(v => {
      if (typeof v === 'string') {
        this.selectedId = null;
        this.filtrar(v);
      } else if (v) {
        this.selectedId = (v as Persona).id ?? null;
      } else {
        this.selectedId = null;
        this.filtrar('');
      }
    });
  }

  displayPersona = (p: Persona | string | null): string => {
    if (!p) return '';
    if (typeof p === 'string') return p;
    return `${p.apellidos || ''} ${p.nombres || ''}`.trim();
  };

  onOptionSelected(p: Persona): void {
    this.selectedId = p?.id ?? null;
  }

  limpiar(): void {
    this.personaCtrl.setValue('');
    this.selectedId = null;
  }

  getProvincia(p: Persona): string {
    return ((p as any)?.provincia_nombre || '').toString();
  }

  isAssigned(personaId?: number | null): boolean {
    if (!personaId) return false;
    return this.assignedIds.has(personaId);
  }

  // Sin persona seleccionada => se guarda como HUECA (personaId = null).
  confirm(): void {
    this.dialogRef.close({
      personaId: this.selectedId,
      cantonId: null,
      horaIngreso: this.horaIngreso || null,
      horaSalida: this.horaSalida || null,
    });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
