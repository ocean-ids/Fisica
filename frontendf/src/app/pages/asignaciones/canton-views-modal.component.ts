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

export interface CantonMixView {
  id: string;
  nombre: string;
  cantonIds: number[];
}

export interface CantonViewsModalData {
  cantones: CantonOption[];
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
    <h2 mat-dialog-title>Nueva Vista De Cantones</h2>
    <mat-dialog-content>
      <mat-form-field class="w-100" appearance="outline">
        <mat-label>Nombre de la vista</mat-label>
        <input matInput [(ngModel)]="viewName" placeholder="Ej: CANTON - CANTON" />
      </mat-form-field>

      <mat-form-field class="w-100" appearance="outline">
        <mat-label>Cantones seleccionados</mat-label>
        <mat-chip-grid #chipGrid aria-label="Seleccion de cantones">
          @for (id of selectedCantonIds; track id) {
            <mat-chip-row (removed)="removeCanton(id)">
              {{ getCantonName(id) }}
              <button matChipRemove [attr.aria-label]="'Quitar ' + getCantonName(id)">
                <mat-icon>cancel</mat-icon>
              </button>
            </mat-chip-row>
          }
        </mat-chip-grid>
        <input
          placeholder="Buscar canton..."
          [(ngModel)]="cantonQuery"
          [matChipInputFor]="chipGrid"
          [matAutocomplete]="auto"
        />
        <mat-autocomplete #auto="matAutocomplete" (optionSelected)="addCanton($event.option.value)">
          @for (c of filteredCantones; track c.id) {
            <mat-option [value]="c.id">{{ c.nombre }}</mat-option>
          }
        </mat-autocomplete>
      </mat-form-field>

      <div class="d-flex gap-2 mb-3">
        <button mat-flat-button color="primary" type="button" (click)="saveView()">Guardar vista</button>
        <button mat-stroked-button type="button" (click)="resetForm()">Limpiar</button>
      </div>

      @if (views.length) {
        <div class="saved-list">
          <div class="fw-semibold mb-2">Vistas guardadas</div>
          @for (v of views; track v.id) {
            <div class="saved-item">
              <div class="saved-title">{{ v.nombre }}</div>
              <div class="saved-chips">
                @for (id of v.cantonIds; track id) {
                  <span class="saved-chip">{{ getCantonName(id) }}</span>
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

    <mat-dialog-actions align="end">
      <button mat-stroked-button type="button" (click)="close()">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
    .saved-list { border-top: 1px solid #e5e7eb; padding-top: 12px; }
    .saved-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
    .saved-title { font-weight: 600; }
    .saved-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .saved-chip { background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 999px; padding: 2px 8px; font-size: 12px; }
    `
  ]
})
export class CantonViewsModalComponent {
  views: CantonMixView[] = [];
  viewName = '';
  selectedCantonIds: number[] = [];
  cantonQuery = '';
  editingId: string | null = null;

  constructor(
    private dialogRef: MatDialogRef<CantonViewsModalComponent, CantonViewsModalResult>,
    @Inject(MAT_DIALOG_DATA) public data: CantonViewsModalData,
  ) {
    this.views = [...(data?.views || [])];
  }

  get filteredCantones(): CantonOption[] {
    const q = (this.cantonQuery || '').trim().toLowerCase();
    const source = (this.data?.cantones || []).filter(c => c.id != null) as Array<CantonOption & { id: number }>;
    return source
      .filter(c => !this.selectedCantonIds.includes(c.id as number))
      .filter(c => !q || (c.nombre || '').toLowerCase().includes(q));
  }

  getCantonName(id: number): string {
    const c = (this.data?.cantones || []).find(x => x.id === id);
    return c?.nombre || `CANTON ${id}`;
  }

  addCanton(id: number): void {
    if (!id || this.selectedCantonIds.includes(id)) return;
    this.selectedCantonIds = [...this.selectedCantonIds, id];
    this.cantonQuery = '';
  }

  removeCanton(id: number): void {
    this.selectedCantonIds = this.selectedCantonIds.filter(x => x !== id);
  }

  saveView(): void {
    const nombre = (this.viewName || '').trim();
    if (!nombre || this.selectedCantonIds.length < 2) return;

    if (this.editingId) {
      this.views = this.views.map(v => v.id === this.editingId
        ? { ...v, nombre, cantonIds: [...this.selectedCantonIds] }
        : v
      );
    } else {
      const id = `view_${Date.now()}`;
      this.views = [...this.views, { id, nombre, cantonIds: [...this.selectedCantonIds] }];
    }
    this.resetForm();
  }

  editView(v: CantonMixView): void {
    this.editingId = v.id;
    this.viewName = v.nombre;
    this.selectedCantonIds = [...v.cantonIds];
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
    this.cantonQuery = '';
  }

  close(): void {
    this.dialogRef.close({ views: this.views });
  }
}
