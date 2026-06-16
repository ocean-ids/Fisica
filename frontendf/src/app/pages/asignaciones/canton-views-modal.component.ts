import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

export interface CantonOption {
  id: number | null;
  nombre: string;
}

export type VistaTipo = 'canton' | 'cliente' | 'persona_tipo';

export const TIPOS_PERSONA: string[] = [
  'FIJOS', 'RETEN', 'CUSTODIO', 'EVENTUAL', 'SACAFRANCO', 'SACAVACACIONES',
  'SUPERVISOR ZONAL', 'SUPERVISOR EVENTUAL', 'SUPERVISOR MOTORIZADO',
  'SUPERVISOR DE ACOMPAÑAMIENTO', 'OPERADOR CENTRO CONTROL', 'SUPERVISOR CENTRO CONTROL',
];

export interface CantonMixView {
  id: string;
  nombre: string;
  tipo: VistaTipo;
  cantonIds: number[];
  clienteIds: number[];
  tipos: string[];
}

export interface CantonViewsModalData {
  cantones: CantonOption[];
  empresas: CantonOption[];
  views: CantonMixView[];
}

export interface CantonViewsModalResult {
  views: CantonMixView[];
}

@Component({
  selector: 'app-canton-views-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
  ],
  template: `
    <h2 mat-dialog-title>Nueva Vista</h2>
    <mat-dialog-content>
      <!-- Selector de tipo de vista -->
      <div class="tipo-toggle-wrap mb-3">
        <div class="tipo-toggle">
          <button type="button"
            [class.active]="tipo === 'canton'"
            (click)="setTipo('canton')">Por cantones</button>
          <button type="button"
            [class.active]="tipo === 'cliente'"
            (click)="setTipo('cliente')">Por empresas</button>
          <button type="button"
            [class.active]="tipo === 'persona_tipo'"
            (click)="setTipo('persona_tipo')">Por tipo</button>
        </div>
      </div>

      <mat-form-field class="w-100" appearance="outline">
        <mat-label>Nombre de la vista</mat-label>
        <input matInput [(ngModel)]="viewName" placeholder="Ej: GUAYAQUIL - DURÁN" />
      </mat-form-field>

      @if (tipo === 'persona_tipo') {
        <div class="tipos-grid mb-3">
          @for (t of tiposDisponibles; track t) {
            <button type="button" class="tipo-chip" [class.sel]="selectedTipos.includes(t)" (click)="toggleTipoPersona(t)">{{ t }}</button>
          }
        </div>
      } @else if (tipo === 'canton') {
        <mat-form-field class="w-100" appearance="outline">
          <mat-label>Cantones seleccionados</mat-label>
          <mat-chip-grid #chipGrid aria-label="Seleccion de cantones">
            @for (id of selectedCantonIds; track id) {
              <mat-chip-row (removed)="removeCanton(id)">
                {{ getName('canton', id) }}
                <button matChipRemove [attr.aria-label]="'Quitar ' + getName('canton', id)">
                  <mat-icon>cancel</mat-icon>
                </button>
              </mat-chip-row>
            }
          </mat-chip-grid>
          <input
            placeholder="Buscar canton..."
            [(ngModel)]="query"
            [matChipInputFor]="chipGrid"
            [matAutocomplete]="autoCanton"
          />
          <mat-autocomplete #autoCanton="matAutocomplete" (optionSelected)="addCanton($event.option.value)">
            @for (c of filteredCantones; track c.id) {
              <mat-option [value]="c.id">{{ c.nombre }}</mat-option>
            }
          </mat-autocomplete>
        </mat-form-field>
      } @else {
        <mat-form-field class="w-100" appearance="outline">
          <mat-label>Empresas seleccionadas</mat-label>
          <mat-chip-grid #chipGridE aria-label="Seleccion de empresas">
            @for (id of selectedClienteIds; track id) {
              <mat-chip-row (removed)="removeCliente(id)">
                {{ getName('cliente', id) }}
                <button matChipRemove [attr.aria-label]="'Quitar ' + getName('cliente', id)">
                  <mat-icon>cancel</mat-icon>
                </button>
              </mat-chip-row>
            }
          </mat-chip-grid>
          <input
            placeholder="Buscar empresa..."
            [(ngModel)]="query"
            [matChipInputFor]="chipGridE"
            [matAutocomplete]="autoCliente"
          />
          <mat-autocomplete #autoCliente="matAutocomplete" (optionSelected)="addCliente($event.option.value)">
            @for (c of filteredEmpresas; track c.id) {
              <mat-option [value]="c.id">{{ c.nombre }}</mat-option>
            }
          </mat-autocomplete>
        </mat-form-field>
      }

      <div class="d-flex gap-2 mb-3">
        <button mat-flat-button color="primary" type="button" (click)="saveView()">Guardar vista</button>
        <button mat-stroked-button type="button" (click)="resetForm()">Limpiar</button>
      </div>

      @if (views.length) {
        <div class="saved-list">
          <div class="fw-semibold mb-2">Vistas guardadas</div>
          @for (v of views; track v.id) {
            <div class="saved-item">
              <div class="saved-title">
                {{ v.nombre }}
                <span class="badge-tipo">{{ v.tipo === 'cliente' ? 'EMPRESAS' : (v.tipo === 'persona_tipo' ? 'TIPOS' : 'CANTONES') }}</span>
              </div>
              <div class="saved-chips">
                @if (v.tipo === 'cliente') {
                  @for (id of v.clienteIds; track id) {
                    <span class="saved-chip">{{ getName('cliente', id) }}</span>
                  }
                } @else if (v.tipo === 'persona_tipo') {
                  @for (t of v.tipos; track t) {
                    <span class="saved-chip">{{ t }}</span>
                  }
                } @else {
                  @for (id of v.cantonIds; track id) {
                    <span class="saved-chip">{{ getName('canton', id) }}</span>
                  }
                }
              </div>
              <div class="d-flex gap-2 mt-2">
                <button mat-stroked-button color="primary" type="button" (click)="editView(v)">Editar</button>
                <button mat-stroked-button color="warn" type="button" (click)="deleteView(v.id)">Eliminar</button>
              </div>
            </div>
          }
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions adockerlign="end">
      <button mat-stroked-button type="button" (click)="close()">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
    .tipo-toggle-wrap { display: flex; justify-content: center; }
    .tipo-toggle { display: inline-flex; border: 1px solid #c7d2fe; border-radius: 999px; overflow: hidden; }
    .tipo-toggle button { border: none; background: #fff; padding: 6px 16px; font-size: 13px; cursor: pointer; color: #4338ca; }
    .tipo-toggle button.active { background: #4338ca; color: #fff; }
    .saved-list { border-top: 1px solid #e5e7eb; padding-top: 12px; }
    .saved-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
    .saved-title { font-weight: 600; display: flex; align-items: center; gap: 8px; }
    .badge-tipo { font-size: 10px; font-weight: 700; background: #eef2ff; color: #4338ca; border: 1px solid #c7d2fe; border-radius: 999px; padding: 1px 8px; }
    .saved-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .saved-chip { background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 999px; padding: 2px 8px; font-size: 12px; }
    .tipos-grid { display: flex; flex-wrap: wrap; gap: 8px; }
    .tipo-chip { border: 1px solid #c7d2fe; background: #fff; color: #4338ca; border-radius: 999px; padding: 6px 12px; font-size: 12px; cursor: pointer; }
    .tipo-chip.sel { background: #4338ca; color: #fff; border-color: #4338ca; }
    `
  ]
})
export class CantonViewsModalComponent {
  views: CantonMixView[] = [];
  viewName = '';
  tipo: VistaTipo = 'canton';
  selectedCantonIds: number[] = [];
  selectedClienteIds: number[] = [];
  selectedTipos: string[] = [];
  readonly tiposDisponibles = TIPOS_PERSONA;
  query = '';
  editingId: string | null = null;

  constructor(
    private dialogRef: MatDialogRef<CantonViewsModalComponent, CantonViewsModalResult>,
    @Inject(MAT_DIALOG_DATA) public data: CantonViewsModalData,
  ) {
    this.views = (data?.views || []).map(v => ({
      ...v,
      tipo: v.tipo || 'canton',
      cantonIds: v.cantonIds || [],
      clienteIds: v.clienteIds || [],
      tipos: v.tipos || [],
    }));
  }

  toggleTipoPersona(t: string): void {
    this.selectedTipos = this.selectedTipos.includes(t)
      ? this.selectedTipos.filter(x => x !== t)
      : [...this.selectedTipos, t];
  }

  setTipo(t: VistaTipo): void {
    if (this.tipo === t) return;
    this.tipo = t;
    this.query = '';
  }

  private filterOptions(source: CantonOption[], excludeIds: number[]): CantonOption[] {
    const q = (this.query || '').trim().toLowerCase();
    return (source || [])
      .filter(c => c.id != null)
      .filter(c => !excludeIds.includes(c.id as number))
      .filter(c => !q || (c.nombre || '').toLowerCase().includes(q));
  }

  get filteredCantones(): CantonOption[] {
    return this.filterOptions(this.data?.cantones || [], this.selectedCantonIds);
  }

  get filteredEmpresas(): CantonOption[] {
    return this.filterOptions(this.data?.empresas || [], this.selectedClienteIds);
  }

  getName(tipo: VistaTipo, id: number): string {
    const source = tipo === 'cliente' ? (this.data?.empresas || []) : (this.data?.cantones || []);
    const c = source.find(x => x.id === id);
    return c?.nombre || `${tipo === 'cliente' ? 'EMPRESA' : 'CANTON'} ${id}`;
  }

  addCanton(id: number): void {
    if (!id || this.selectedCantonIds.includes(id)) return;
    this.selectedCantonIds = [...this.selectedCantonIds, id];
    this.query = '';
  }

  removeCanton(id: number): void {
    this.selectedCantonIds = this.selectedCantonIds.filter(x => x !== id);
  }

  addCliente(id: number): void {
    if (!id || this.selectedClienteIds.includes(id)) return;
    this.selectedClienteIds = [...this.selectedClienteIds, id];
    this.query = '';
  }

  removeCliente(id: number): void {
    this.selectedClienteIds = this.selectedClienteIds.filter(x => x !== id);
  }

  saveView(): void {
    const nombre = (this.viewName || '').trim();
    if (!nombre) return;
    if (this.tipo === 'canton' && this.selectedCantonIds.length < 2) return;
    if (this.tipo === 'cliente' && this.selectedClienteIds.length < 1) return;
    if (this.tipo === 'persona_tipo' && this.selectedTipos.length < 1) return;

    const nueva: Omit<CantonMixView, 'id'> = {
      nombre,
      tipo: this.tipo,
      cantonIds: this.tipo === 'canton' ? [...this.selectedCantonIds] : [],
      clienteIds: this.tipo === 'cliente' ? [...this.selectedClienteIds] : [],
      tipos: this.tipo === 'persona_tipo' ? [...this.selectedTipos] : [],
    };

    if (this.editingId) {
      this.views = this.views.map(v => v.id === this.editingId ? { ...v, ...nueva } : v);
    } else {
      this.views = [...this.views, { id: `view_${Date.now()}`, ...nueva }];
    }
    this.resetForm();
  }

  editView(v: CantonMixView): void {
    this.editingId = v.id;
    this.viewName = v.nombre;
    this.tipo = v.tipo || 'canton';
    this.selectedCantonIds = [...(v.cantonIds || [])];
    this.selectedClienteIds = [...(v.clienteIds || [])];
    this.selectedTipos = [...(v.tipos || [])];
  }

  deleteView(id: string): void {
    this.views = this.views.filter(v => v.id !== id);
    if (this.editingId === id) {
      this.resetForm();
    }
  }

  resetForm(): void {
    this.editingId = null;
    this.viewName = '';
    this.selectedCantonIds = [];
    this.selectedClienteIds = [];
    this.selectedTipos = [];
    this.query = '';
  }

  close(): void {
    this.dialogRef.close({ views: this.views });
  }
}
