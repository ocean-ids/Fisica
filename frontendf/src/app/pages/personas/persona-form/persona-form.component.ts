import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTabsModule } from '@angular/material/tabs';
import { Persona } from '../../../models/persona.model';
import { UbicacionService } from '../../../services/ubicacion.service';
import { ProvinciasService } from '../../../services/provincias.service';
import { ClienteService } from '../../../services/cliente.service';
import { PersonaService } from '../../../services/persona.service';
import { Province, City } from '../../../data/provincias';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-persona-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatRadioModule,
    MatCheckboxModule,
    MatSlideToggleModule,
    MatTabsModule
  ],
  templateUrl: './persona-form.component.html',
  styleUrl: './persona-form.component.scss'
})
export class PersonaFormComponent implements OnInit {
  personaForm!: FormGroup;
  provincias: (any | Province)[] = [];
  cantones: (any | City)[] = [];
  parroquias: { id: number; nombre: string }[] = [];
  clientes: { id: number; nombre: string }[] = [];
  instalaciones: { id: number; nombre: string }[] = [];
  private initialSeccion: string | null = null;
  fotoFile: File | null = null;
  fotoPreview: string | null = null;
  // Documentos (rutas compartidas) — pestaña Referencias
  documentos: { tipo: string; nombre_archivo: string; ruta_archivo: string; extension: string }[] = [];
  tiposDocumento = ['PDF GENERAL', 'CÉDULA', 'CERTIFICADO', 'CONTRATO', 'FOTO', 'OTRO'];
  // Más Referencias (4 listas)
  experiencias: { empresa: string; puesto_cargo: string; tiempo: string; motivo_salida: string }[] = [];
  referenciasPersonales: { persona_contactar: string; relacion: string; telefonos: string; comentario: string }[] = [];
  nivelesEstudio: { nivel_estudio: string; completa: boolean; centro_capacitacion: string }[] = [];
  formaciones: { centro_capacitacion: string; curso: string; area: string; horas: number }[] = [];
  // Certificados (catálogo + marcados)
  certTipos: { id: number; nombre: string; grupo: string; orden: number }[] = [];
  certMarcados = new Set<number>();
  certArchivos: Record<number, string> = {};
  certSubiendo: number | null = null;
  private personaId: number | null = null;
  sexos = [{ v: 'MASCULINO', l: 'Masculino' }, { v: 'FEMENINO', l: 'Femenino' }];
  estadosCiviles = [{ v: 'SOLTERO', l: 'Soltero' }, { v: 'CASADO', l: 'Casado' }, {v: 'DIVORCIADO', l: 'Divorciado'}, {v: 'UNION LIBRE', l:'Unión Libre'},{ v: 'VIUDO', l: 'Viudo' },];
  tiposEmpleado = [{ v: 'EMPLEADO', l: 'Empleado' }, { v: 'OBRERO', l: 'Obrero o Eventual' }, { v: 'OPERADOR', l: 'Operador' }];
  regiones = [{ v: 'SIERRA', l: 'Sierra' }, { v: 'COSTA', l: 'Costa' }];
  unidadesNegocio = [
    { v: 'SEGURIDAD FISICA', l: 'Seguridad Física' },
    { v: 'SEGURIDAD DE CARGA', l: 'Seguridad de Carga' },
  ];
  perfiles = [
    { v: 'SENSIBLE', l: 'Sensible' }, { v: 'RIGIDO', l: 'Rígido' }, { v: 'INDUSTRIAL', l: 'Industrial' },
    { v: 'CUSTODIA', l: 'Custodia' }, { v: 'OTROS', l: 'Otros' },
  ];
  nacionalidades = ['Ecuatoriana', 'Extranjero', 'Otros'];
  formasPago = [
    { v: 'MENSUAL', l: 'Mensual' }, { v: 'QUINCENAL', l: 'Quincenal' }, { v: 'SEMANAL', l: 'Semanal' },
  ];
  motivosSalida = [
    { v: 'RENUNCIA VOLUNTARIA', l: 'Renuncia Voluntaria' }, { v: 'DESPIDO', l: 'Despido' },
    { v: 'VISTO BUENO', l: 'Visto Bueno' }, { v: 'TERMINACIÓN DE CONTRATO', l: 'Terminación de Contrato' },
    { v: 'PROBLEMAS FAMILIARES', l: 'Problemas Familiares' }, { v: 'MEJOR PROPUESTA DE TRABAJO', l: 'Mejor Propuesta de Trabajo' },
  ];
  bancos = [
    'Banco Pichincha', 'Banco del Pacífico', 'Banco Guayaquil', 'Produbanco',
    'Banco Internacional', 'Banco Bolivariano', 'Banco del Austro', 'Banco de Machala',
    'Banco ProCredit', 'Banco Solidario', 'Banco General Rumiñahui', 'Banco Amazonas',
    'Banco del Litoral', 'Banco Coopnacional', 'Banco Capital', 'BanEcuador',
    'Cooperativa JEP', 'Cooperativa Jardín Azuayo', 'Cooperativa Policía Nacional',
    'Cooperativa 29 de Octubre', 'Cooperativa Cooprogreso', 'Cooperativa Alianza del Valle',
  ];
  private useStaticProvincias = false;
  private initialCanton: string | null = null;
  private initialCantonName: string | null = null;
  private initialProvinciaName: string | null = null;
  private initialParroquia: string | null = null;
  tipos: Persona['tipo'][] = [
    'FIJOS',
    'RETEN',
    'CUSTODIO',
    'EVENTUAL',
    'SACAFRANCO',
    'SACAVACACIONES',
    'SUPERVISOR ZONAL',
    'SUPERVISOR EVENTUAL',
    'SUPERVISOR MOTORIZADO',
    'SUPERVISOR DE ACOMPAÑAMIENTO',
    'OPERADOR CENTRO CONTROL',
    'SUPERVISOR CENTRO CONTROL',
  ];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<PersonaFormComponent>,
    @Inject(MAT_DIALOG_DATA) public persona: Persona,
    private ubicacionService: UbicacionService,
    private provinciasService: ProvinciasService,
    private clienteService: ClienteService,
    private personaService: PersonaService
  ) {}

  ngOnInit(): void {
    const p: any = this.persona || {};
    this.personaForm = this.fb.group({
      // Datos base de la app
      cedula: [p.cedula || '', [Validators.required, Validators.pattern('^[0-9]{1,10}$'), Validators.maxLength(10)]],
      nombres: [p.nombres || '', Validators.required],
      apellidos: [p.apellidos || '', Validators.required],
      tipo: [p.tipo ?? 'FIJOS', Validators.required],
      provincia: [p.provincia ?? null],
      canton: [p.canton ?? null],
      is_active: [p.is_active ?? true],
      // Datos del ERP
      codigo_erp: [p.codigo_erp || ''],
      centro_costo: [p.centro_costo || ''],
      sexo: [p.sexo || ''],
      estatura: [p.estatura ?? null],
      lugar_nacimiento: [p.lugar_nacimiento || ''],
      fecha_nacimiento: [p.fecha_nacimiento || null],
      direccion: [p.direccion || ''],
      parroquia: [p.parroquia || ''],
      estado_civil: [p.estado_civil || ''],
      telefono: [p.telefono || '', Validators.pattern('^[0-9]*$')],
      conyuge: [p.conyuge || ''],
      nacionalidad: [p.nacionalidad || ''],
      cliente: [p.cliente ?? null],
      unidad_negocio: [p.unidad_negocio || 'SEGURIDAD FISICA'],
      tipo_empleado: [p.tipo_empleado || ''],
      cargo: [p.cargo || 'AGENTE DE SEGURIDAD G'],
      fecha_ingreso: [p.fecha_ingreso || null],
      fecha_salida: [p.fecha_salida || null],
      forma_pago: [p.forma_pago || ''],
      numero_afiliacion: [p.numero_afiliacion || ''],
      numero_contrato: [p.numero_contrato || ''],
      actividad: [p.actividad || ''],
      seccion: [p.seccion || ''],
      departamento: [p.departamento || ''],
      perfil: [p.perfil || ''],
      fecha_pago_liquidacion: [p.fecha_pago_liquidacion || null],
      motivo_salida: [p.motivo_salida || ''],
      correo_personal: [p.correo_personal || ''],
      region: [p.region || ''],
      gypaseg: [p.gypaseg ?? false],
      affis: [p.affis ?? false],
      pbip: [p.pbip ?? false],
      // Nómina (Ingresos / Descuentos) — pestaña "Ingresos Dctos."
      nomina: this.fb.group({
        // Sueldo y Beneficios de Ley
        sueldo: [0], desc_genesis: [0], bonificacion: [0], transporte: [0], compensacion: [0],
        horas_25: [0], horas_50: [0], horas_100: [0],
        pagar_fondo_reserva: [false], observaciones: [''],
        // Acumulados de Beneficios Sociales
        decimo_tercer: [0], decimo_cuarto: [0], vacaciones: [0], fondo_reserva: [0],
        pagar_rol_10mo_3ero: [false], pagar_rol_10mo_4to: [false], pagar_rol_vacaciones: [false],
        desc_aporte_conyuge: [false], giro_contable_liquidacion: [false],
        numero_liquidacion_ministerio: [''],
        // Rol Extra
        moviliza: [0], lunch: [0], anticipo_22: [0], viaticos: [0], descuento: [0], ingreso_extra: [0],
        concepto: [''],
        // Subsidio
        subsidio_enfermedad: [false], subsidio_enfermedad_pct: [0],
        subsidio_accidente: [false], subsidio_accidente_pct: [0],
        subsidio_maternidad: [false], subsidio_maternidad_pct: [0],
      }),
      // Otros Datos (bancario / contable / vacaciones / cargas / gastos) — pestaña "Otros Datos"
      otros_datos: this.fb.group({
        incluir_en_rol: [true], acreditar: [false],
        ultima_liquidacion: [null], grupo_sanguineo: [''],
        banco: [''], cuenta_ahorros: [''], cuenta_corriente: [''],
        fecha_ini_vacaciones: [null], fecha_fin_vacaciones: [null], dias_vacaciones: [0],
        codigo_cuenta: [''], cuenta_departamento: [''], cuenta_auxiliar: [''],
        numero_cargas: [0],
        gasto_salud: [0], gasto_vestimenta: [0], gasto_educacion: [0], gasto_vivienda: [0],
        gasto_alimentacion: [0], gasto_arte_cultura: [0], gasto_turismo: [0],
      }),
      // Referencias (datos referenciales / estudios / servicios) — pestaña "Referencias"
      referencias: this.fb.group({
        cedula_militar: [''], observacion: [''], edad: [null], maniobras: [''],
        carnet_conadis: [''], numero_certificado_votacion: [''], licencia_conducir: [''],
        codigo_iess: [''], certificado_violencia_intrafamiliar: [''],
        primaria: [false], secundaria: [false], universidad: [false],
        titulo: [''], anios_estudio: [0],
        miembro_fuerza_publica: [false], realizo_servicio_militar: [false],
        contrato_inspectoria: [''],
      }),
    });

    // Al editar, cargar la nómina y otros datos existentes del empleado.
    if (p.id) {
      this.personaService.getNomina(p.id).subscribe({
        next: (n) => { if (n) this.personaForm.get('nomina')?.patchValue(n); },
        error: () => {}
      });
      this.personaService.getOtrosDatos(p.id).subscribe({
        next: (o) => {
          if (o) {
            const banco = (o.banco || '').toString().trim();
            if (banco && !this.bancos.includes(banco)) this.bancos = [banco, ...this.bancos];
            this.personaForm.get('otros_datos')?.patchValue(o);
          }
        },
        error: () => {}
      });
      this.personaService.getReferencias(p.id).subscribe({
        next: (r) => { if (r) this.personaForm.get('referencias')?.patchValue(r); },
        error: () => {}
      });
      this.personaService.getDocumentos(p.id).subscribe({
        next: (docs) => { this.documentos = (docs || []).map(d => ({
          tipo: d.tipo || 'PDF GENERAL', nombre_archivo: d.nombre_archivo || '',
          ruta_archivo: d.ruta_archivo || '', extension: d.extension || ''
        })); },
        error: () => {}
      });
      this.personaService.getMasReferencias(p.id).subscribe({
        next: (m) => {
          this.experiencias = m?.experiencias || [];
          this.referenciasPersonales = m?.referencias_personales || [];
          this.nivelesEstudio = m?.niveles_estudio || [];
          this.formaciones = m?.formaciones || [];
        },
        error: () => {}
      });
      this.personaId = p.id;
    }
    // El catálogo de certificados siempre se muestra (también en empleado nuevo).
    this.cargarCertificados(p.id || null);

    this.onUnidadNegocioChange();  // ajusta "Tipo" según la unidad (Física vs Carga)
    this.loadProvincias();
    this.initialSeccion = ((this.persona as any)?.seccion || '').trim() || null;
    this.clienteService.getClientes().subscribe({
      next: (list: any[]) => { this.clientes = (list || []).map(c => ({ id: c.id, nombre: c.razon_social || c.nombre_comercial })); },
      error: () => { this.clientes = []; }
    });
    if (p.cliente) this.loadInstalaciones(p.cliente, true);
  }

  // Seguridad de Carga: registro de personal (sin "Tipo"/clasificación de turnos).
  get esCarga(): boolean {
    return (this.personaForm?.get('unidad_negocio')?.value || '')
      .toString().toUpperCase().includes('CARGA');
  }

  onUnidadNegocioChange(): void {
    const tipo = this.personaForm.get('tipo');
    if (!tipo) return;
    if (this.esCarga) {
      tipo.clearValidators();
      tipo.setValue(null);
    } else {
      tipo.setValidators([Validators.required]);
      if (!tipo.value) tipo.setValue('FIJOS');
    }
    tipo.updateValueAndValidity();
  }

  onProvinciaChange(): void {
    const provinciaId = this.personaForm.get('provincia')?.value;
    if (!provinciaId) {
      this.cantones = [];
      this.personaForm.get('canton')?.setValue(null);
      return;
    }
    if (this.useStaticProvincias) {
      const prov = (this.provincias as Province[]).find(x => x.id === provinciaId);
      this.cantones = prov ? prov.ciudades : [];
      this.afterCantonesLoaded();
    } else {
      this.ubicacionService.getCantones(provinciaId).subscribe((cants: any[]) => {
        this.cantones = cants || [];
        this.afterCantonesLoaded();
      });
    }
  }

  private loadProvincias(): void {
    this.initialCanton = (this.persona?.canton as any) ?? null;
    this.initialCantonName = (this.persona?.canton_nombre || '').trim().toUpperCase() || null;
    this.initialProvinciaName = (this.persona?.provincia_nombre || '').trim().toUpperCase() || null;
    this.initialParroquia = ((this.persona as any)?.parroquia || '').trim().toUpperCase() || null;

    const applyInitialProvincia = () => {
      const storedProvId = this.persona?.provincia ?? null;
      const provFoundById = storedProvId
        ? this.provincias.find((x: any) => x.id === storedProvId)
        : null;
      const provFoundByName = this.initialProvinciaName
        ? this.provincias.find((x: any) => (x.nombre || '').toUpperCase() === this.initialProvinciaName)
        : null;
      const provFound = provFoundById || provFoundByName;
      if (provFound) {
        this.personaForm.get('provincia')?.setValue(provFound.id);
        this.onProvinciaChange();
      }
    };

    this.useStaticProvincias = false;
    this.ubicacionService.getProvincias().subscribe({
      next: (list) => {
        this.provincias = list || [];
        applyInitialProvincia();
      },
      error: () => {
        this.useStaticProvincias = true;
        this.provincias = this.provinciasService.getProvinciasSync();
        applyInitialProvincia();
      }
    });
  }

  private afterCantonesLoaded(): void {
    if (this.initialCanton || this.initialCantonName) {
      const foundById = this.initialCanton
        ? this.cantones.find((x: any) => x.id === this.initialCanton)
        : null;
      const foundByName = this.initialCantonName
        ? this.cantones.find((x: any) => (x.nombre || '').toUpperCase() === this.initialCantonName)
        : null;
      const found = foundById || foundByName;
      if (found) {
        this.personaForm.get('canton')?.setValue(found.id);
        this.loadParroquias(found.id, true);
        this.initialCanton = null;
        this.initialCantonName = null;
        return;
      }
      this.initialCanton = null;
      this.initialCantonName = null;
    }
    const current = this.personaForm.get('canton')?.value;
    if (current && this.cantones.find((x: any) => x.id === current)) {
      return;
    }
    this.personaForm.get('canton')?.setValue(null);
    this.parroquias = [];
  }

  // Cargar parroquias del cantón (cascada Cantón -> Parroquia).
  loadParroquias(cantonId: number | null, keepInitial = false): void {
    if (!cantonId) {
      this.parroquias = [];
      if (!keepInitial) this.personaForm.get('parroquia')?.setValue('');
      return;
    }
    this.ubicacionService.getParroquias(cantonId).subscribe({
      next: (list) => {
        this.parroquias = list || [];
        // Conservar el valor guardado aunque no esté exacto en la lista.
        const stored = keepInitial ? this.initialParroquia : this.personaForm.get('parroquia')?.value;
        if (stored && !this.parroquias.some(p => (p.nombre || '').toUpperCase() === String(stored).toUpperCase())) {
          this.parroquias = [{ id: -1, nombre: String(stored).toUpperCase() }, ...this.parroquias];
        }
        if (keepInitial && this.initialParroquia) {
          this.personaForm.get('parroquia')?.setValue(this.initialParroquia);
          this.initialParroquia = null;
        }
      },
      error: () => { this.parroquias = []; }
    });
  }

  onCantonChange(): void {
    this.personaForm.get('parroquia')?.setValue('');
    this.loadParroquias(this.personaForm.get('canton')?.value ?? null, false);
  }

  // Cliente -> Sección: la sección lista las instalaciones del cliente seleccionado.
  loadInstalaciones(clienteId: number | null, keepInitial = false): void {
    if (!clienteId) {
      this.instalaciones = [];
      if (!keepInitial) this.personaForm.get('seccion')?.setValue('');
      return;
    }
    this.ubicacionService.getInstalaciones(clienteId).subscribe({
      next: (list: any[]) => {
        this.instalaciones = (list || []).map(i => ({ id: i.id, nombre: i.nombre }));
        const stored = keepInitial ? this.initialSeccion : this.personaForm.get('seccion')?.value;
        if (stored && !this.instalaciones.some(i => (i.nombre || '').toUpperCase() === String(stored).toUpperCase())) {
          this.instalaciones = [{ id: -1, nombre: String(stored) }, ...this.instalaciones];
        }
        if (keepInitial && this.initialSeccion) {
          this.personaForm.get('seccion')?.setValue(this.initialSeccion);
          this.initialSeccion = null;
        }
      },
      error: () => { this.instalaciones = []; }
    });
  }

  onClienteChange(): void {
    this.personaForm.get('seccion')?.setValue('');
    this.loadInstalaciones(this.personaForm.get('cliente')?.value ?? null, false);
  }

  soloNumeros(event: KeyboardEvent): void {
    // Permite teclas de control (Backspace, Tab, flechas, Supr, etc.) y atajos
    if (event.key.length > 1 || event.ctrlKey || event.metaKey) {
      return;
    }
    // Bloquea cualquier caracter que no sea digito
    if (!/[0-9]/.test(event.key)) {
      event.preventDefault();
    }
  }

  addDocumento(): void {
    this.documentos.push({ tipo: 'PDF GENERAL', nombre_archivo: '', ruta_archivo: '', extension: '' });
  }

  removeDocumento(i: number): void {
    this.documentos.splice(i, 1);
  }

  addExperiencia(): void { this.experiencias.push({ empresa: '', puesto_cargo: '', tiempo: '', motivo_salida: '' }); }
  removeExperiencia(i: number): void { this.experiencias.splice(i, 1); }
  addReferenciaPersonal(): void { this.referenciasPersonales.push({ persona_contactar: '', relacion: '', telefonos: '', comentario: '' }); }
  removeReferenciaPersonal(i: number): void { this.referenciasPersonales.splice(i, 1); }
  addNivelEstudio(): void { this.nivelesEstudio.push({ nivel_estudio: '', completa: false, centro_capacitacion: '' }); }
  removeNivelEstudio(i: number): void { this.nivelesEstudio.splice(i, 1); }
  addFormacion(): void { this.formaciones.push({ centro_capacitacion: '', curso: '', area: '', horas: 0 }); }
  removeFormacion(i: number): void { this.formaciones.splice(i, 1); }

  // ---- Certificados ----
  private cargarCertificados(id: number | null): void {
    const obs = id
      ? this.personaService.getCertificados(id)
      : this.personaService.getCatalogoCertificados();
    obs.subscribe({
      next: (res) => {
        this.certTipos = res?.tipos || [];
        this.certMarcados = new Set<number>(res?.marcados || []);
        this.certArchivos = res?.archivos || {};
        this.rebuildCertGrupos();
      },
      error: () => {}
    });
  }

  onCertFileSelected(tipoId: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files.length ? input.files[0] : null;
    if (!file) return;
    if (!this.personaId) {
      Swal.fire({ icon: 'info', title: 'Guarda primero el empleado', text: 'Debes guardar el empleado para poder adjuntar archivos.', confirmButtonColor: '#0c2f5a' });
      return;
    }
    this.certSubiendo = tipoId;
    this.personaService.subirArchivoCertificado(this.personaId, tipoId, file).subscribe({
      next: (res) => {
        if (res?.archivo) this.certArchivos = { ...this.certArchivos, [tipoId]: res.archivo };
        this.certMarcados.add(tipoId);
        this.certSubiendo = null;
        Swal.fire({ icon: 'success', title: 'Archivo subido', timer: 1000, showConfirmButton: false });
      },
      error: (err) => {
        this.certSubiendo = null;
        const detalle = err?.status ? ` (HTTP ${err.status})` : '';
        Swal.fire({ icon: 'error', title: 'No se pudo subir', text: (err?.error?.error || '') + detalle, confirmButtonColor: '#0c2f5a' });
      }
    });
    input.value = '';
  }

  certGrupos: { grupo: string; tipos: any[] }[] = [];

  private rebuildCertGrupos(): void {
    const grupos: { grupo: string; tipos: any[] }[] = [];
    for (const t of this.certTipos) {
      const g = t.grupo || 'Otros';
      let bucket = grupos.find(x => x.grupo === g);
      if (!bucket) { bucket = { grupo: g, tipos: [] }; grupos.push(bucket); }
      bucket.tipos.push(t);
    }
    this.certGrupos = grupos;
  }

  trackByGrupo(_i: number, g: { grupo: string }): string { return g.grupo; }
  trackByTipoId(_i: number, t: { id: number }): number { return t.id; }

  get certProgreso(): { hechos: number; total: number; pct: number } {
    const total = this.certTipos.length;
    const hechos = this.certTipos.filter(t => this.certMarcados.has(t.id)).length;
    return { hechos, total, pct: total ? Math.round((hechos / total) * 100) : 0 };
  }

  toggleCert(id: number, marcado: boolean): void {
    if (marcado) this.certMarcados.add(id);
    else this.certMarcados.delete(id);
  }

  quitarArchivoCert(tipoId: number): void {
    if (!this.personaId) return;
    Swal.fire({
      icon: 'warning',
      title: '¿Quitar el archivo?',
      text: 'Se eliminará el documento de este certificado.',
      showCancelButton: true,
      confirmButtonText: 'Quitar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#b91c1c',
    }).then((res) => {
      if (!res.isConfirmed) return;
      this.personaService.eliminarArchivoCertificado(this.personaId as number, tipoId).subscribe({
        next: () => {
          const copia = { ...this.certArchivos };
          delete copia[tipoId];
          this.certArchivos = copia;
          this.certMarcados.delete(tipoId);
          Swal.fire({ icon: 'success', title: 'Archivo quitado', timer: 1000, showConfirmButton: false });
        },
        error: () => Swal.fire({ icon: 'error', title: 'No se pudo quitar', confirmButtonColor: '#0c2f5a' })
      });
    });
  }

  agregarCertificado(): void {
    Swal.fire({
      title: 'Nuevo certificado',
      input: 'text',
      inputLabel: 'Nombre del certificado',
      inputPlaceholder: 'Ej. Carné COVID',
      showCancelButton: true,
      confirmButtonText: 'Agregar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#0c2f5a',
      inputValidator: (v) => (!v || !v.trim() ? 'Escribe un nombre' : null),
    }).then((res) => {
      const nombre = (res.value || '').trim();
      if (!res.isConfirmed || !nombre) return;
      this.personaService.crearTipoCertificado(nombre).subscribe({
        next: (t) => {
          if (t?.id && !this.certTipos.some(x => x.id === t.id)) {
            this.certTipos = [...this.certTipos, { id: t.id, nombre: t.nombre, grupo: t.grupo, orden: t.orden }];
            this.rebuildCertGrupos();
          }
          Swal.fire({ icon: 'success', title: 'Certificado agregado', timer: 1200, showConfirmButton: false });
        },
        error: () => Swal.fire({ icon: 'error', title: 'No se pudo agregar', confirmButtonColor: '#0c2f5a' })
      });
    });
  }

  onFotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files && input.files.length ? input.files[0] : null;
    this.fotoFile = file;
    if (file) {
      const reader = new FileReader();
      reader.onload = () => { this.fotoPreview = reader.result as string; };
      reader.readAsDataURL(file);
    }
  }

  onSubmit(): void {
    if (this.personaForm.valid) {
      this.dialogRef.close({
        ...this.personaForm.value,
        _fotoFile: this.fotoFile,
        _documentos: this.documentos,
        _masReferencias: {
          experiencias: this.experiencias,
          referencias_personales: this.referenciasPersonales,
          niveles_estudio: this.nivelesEstudio,
          formaciones: this.formaciones,
        },
        _certificados: Object.keys(this.certArchivos).map(Number),
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
