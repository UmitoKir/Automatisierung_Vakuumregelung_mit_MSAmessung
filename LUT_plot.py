import CSVManager
import Mathfunctions
import numpy as np
import matplotlib.pyplot as plt


def main():
    MATH = Mathfunctions.Interpolation()
    pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    CSV = CSVManager.CSVReader(pfad)
    CSV.extractDataForLUT()

    p_min = max(min(CSV.stab_druck_einlass_fallend), min(CSV.stab_druck_einlass_steigend))
    p_max = min(max(CSV.stab_druck_einlass_fallend), max(CSV.stab_druck_einlass_steigend))
    p_interp = np.linspace(p_min, p_max, 500)
    
    x_fallend, y_fallend = MATH.x_interpoliert(CSV.stab_v_einlass_fallend, CSV.stab_druck_einlass_fallend)
    x_steigend, y_steigend = MATH.x_interpoliert(CSV.stab_v_einlass_steigend, CSV.stab_druck_einlass_steigend)

    plt.figure(1,figsize=(10, 6))
    plt.plot(CSV.stab_v_einlass_fallend, CSV.stab_druck_einlass_fallend, 'o-', color='black', linewidth=1.5, label='Messpunkte fallend')
    plt.plot(CSV.stab_v_einlass_steigend, CSV.stab_druck_einlass_steigend, 'o-', color='grey', linewidth=1.5, label='Messpunkte steigend')
    plt.plot(x_fallend, y_fallend, color='blue', linewidth=1.5, label='PCHIP-Interpolation fallend')
    plt.plot(x_steigend, y_steigend, color='violet', linewidth=1.5, label='PCHIP-Interpolation steigend')
    plt.gca().invert_xaxis()
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (lin) Einlassventil")
    plt.xlabel("Einlassventilspannung [V]")
    plt.ylabel("Druck [mbar]")
    plt.legend()
    plt.tight_layout()

    plt.figure(2,figsize=(10, 6))
    plt.plot(CSV.stab_v_einlass_fallend, CSV.stab_druck_einlass_fallend, 'o-', color='black', linewidth=1.5, label='Messpunkte fallend')
    plt.plot(CSV.stab_v_einlass_steigend, CSV.stab_druck_einlass_steigend, 'o-', color='grey', linewidth=1.5, label='Messpunkte steigend')
    plt.plot(x_fallend, y_fallend, color='blue', linewidth=1.5, label='PCHIP-Interpolation fallend')
    plt.plot(x_steigend, y_steigend, color='violet', linewidth=1.5, label='PCHIP-Interpolation steigend')
    plt.gca().invert_xaxis()
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (log) Einlassventil")
    plt.xlabel("Einlassventilspannung [V]")
    plt.ylabel("Druck [mbar]")
    plt.legend()
    plt.tight_layout()

    plt.show()

if __name__ == "__main__":
    main()
