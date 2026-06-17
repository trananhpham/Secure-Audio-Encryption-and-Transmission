class SecureAudioError(Exception):
    """Base exception for all secure audio transfer errors."""
    pass

class InvalidAudioFileError(SecureAudioError):
    pass

class UnsupportedFormatError(SecureAudioError):
    pass

class InputSegmentError(SecureAudioError):
    pass

class InvalidManifestError(SecureAudioError):
    pass

class ManifestAuthenticationError(SecureAudioError):
    pass

class MissingSegmentError(SecureAudioError):
    pass

class DuplicateSegmentError(SecureAudioError):
    pass

class UnexpectedSegmentError(SecureAudioError):
    pass

class SegmentOrderError(SecureAudioError):
    pass

class SegmentIntegrityError(SecureAudioError):
    pass

class DecryptionError(SecureAudioError):
    pass

class WrongKeyError(SecureAudioError):
    pass

class FormatMismatchError(SecureAudioError):
    pass

class AudioCompatibilityError(SecureAudioError):
    pass

class AssemblyError(SecureAudioError):
    pass

class FinalHashMismatchError(SecureAudioError):
    pass

class ReplayDetectedError(SecureAudioError):
    pass
